# from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from datetime import datetime
from django.utils.timezone import now
import pandas as pd
from sklearn.cluster import KMeans
import os
import uuid

from .models import Customer, Purchase, PurchaseItem, Product
from django.db.models import Count, Sum, Q


# -------------------------- AI Analytic functions  -------------------

class PurchaseCategoryPreferencesView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            # Define age groups
            age_groups = {
                '18–25': Q(age__gte=18, age__lte=25),
                '26–35': Q(age__gte=26, age__lte=35),
                '36–50': Q(age__gte=36, age__lte=50),
                '51+': Q(age__gte=51),
                'Unknown': Q(age__isnull=True),
            }

            response_data = {}

            for age_label, age_filter in age_groups.items():
                age_group_data = {}
                gender_groups = ['Male', 'Female', 'Non-binary', 'Other', None]

                for gender in gender_groups:
                    gender_filter = Q(gender=gender) if gender else Q(gender__isnull=True)
                    customers = Customer.objects.filter(age_filter & gender_filter)

                    if not customers.exists():
                        continue

                    purchases = Purchase.objects.filter(customer__in=customers)
                    items = PurchaseItem.objects.filter(purchase__in=purchases)

                    category_stats = (
                        items.values('product__category')
                        .annotate(
                            total_quantity=Sum('quantity'),
                            total_revenue=Sum('price_at_purchase')
                        )
                        .order_by('-total_quantity')
                    )

                    gender_label = gender if gender else 'Unspecified'
                    age_group_data[gender_label] = list(category_stats)

                response_data[age_label] = age_group_data

            return Response({
                'message': 'Category preferences by age and gender retrieved successfully.',
                'preferences': response_data
            })

        except Exception as e:
            return Response({'error': str(e)}, status=500)


class DiscountUsageAnalysisView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            # Age group buckets
            age_groups = {
                '18–25': Q(age__gte=18, age__lte=25),
                '26–35': Q(age__gte=26, age__lte=35),
                '36–50': Q(age__gte=36, age__lte=50),
                '51+': Q(age__gte=51),
                'Unknown': Q(age__isnull=True),
            }

            result = {}
            for label, age_filter in age_groups.items():
                customers = Customer.objects.filter(age_filter)
                purchases = Purchase.objects.filter(customer__in=customers)

                with_discount = purchases.filter(discount_applied=True)
                without_discount = purchases.filter(discount_applied=False)

                result[label] = {
                    'total_customers': customers.count(),
                    'purchases_with_discount': with_discount.count(),
                    'revenue_with_discount': with_discount.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
                    'purchases_without_discount': without_discount.count(),
                    'revenue_without_discount': without_discount.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
                }

            return Response({
                'message': 'Discount usage analysis completed.',
                'discount_usage_by_age_group': result
            })

        except Exception as e:
            return Response({'error': str(e)}, status=500)


class TopProductsView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            # Aggregate quantity and revenue per product
            top_products = (
                PurchaseItem.objects
                .values('product__id', 'product__name', 'product__category')
                .annotate(total_quantity=Sum('quantity'), total_revenue=Sum('price_at_purchase'))
                .order_by('-total_quantity')[:10]
            )

            return Response({
                'message': 'Top products retrieved successfully.',
                'top_products': list(top_products)
            })

        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ExternalCustomerSegmentationView(APIView):
    def get(self, request, *args, **kwargs):
        file_name = request.query_params.get('file')
        if not file_name:
            return Response({'error': 'Missing "file" query parameter.'}, status=400)

        file_path = os.path.join(os.getcwd(), 'media', file_name)
        if not os.path.exists(file_path):
            return Response({'error': f'File "{file_name}" not found.'}, status=404)

        try:
            df = pd.read_csv(file_path)
            required_columns = ['CustomerID', 'TotalSpend', 'PurchaseFrequency', 'LastPurchaseDays']
            if not all(col in df.columns for col in required_columns):
                return Response({'error': f'Missing required columns: {required_columns}'}, status=400)

            features = df[['TotalSpend', 'PurchaseFrequency', 'LastPurchaseDays']]
            kmeans = KMeans(n_clusters=3, random_state=42)
            df['Segment'] = kmeans.fit_predict(features)

            # Calculate means per segment
            segment_means = df.groupby('Segment')[['TotalSpend', 'PurchaseFrequency', 'LastPurchaseDays']].mean()
            labeled_segments = {}

            # Sort segments based on TotalSpend and Frequency
            for segment_id in segment_means.index:
                spend = segment_means.loc[segment_id, 'TotalSpend']
                freq = segment_means.loc[segment_id, 'PurchaseFrequency']
                recency = segment_means.loc[segment_id, 'LastPurchaseDays']

                # Heuristic labeling
                if spend > 800 and freq > 7 and recency < 10:
                    label = 'High Value'
                elif spend > 500 and freq > 4:
                    label = 'Mid-Tier'
                else:
                    label = 'At Risk'

                labeled_segments[segment_id] = label

            # Replace numeric segments with labels in preview
            df['SegmentLabel'] = df['Segment'].map(labeled_segments)
            preview = df[['CustomerID', 'TotalSpend', 'PurchaseFrequency', 'LastPurchaseDays', 'SegmentLabel']].head(10).to_dict(orient='records')

            # Summary: count of labeled segments
            label_counts = df['SegmentLabel'].value_counts().to_dict()

            return Response({
                'message': 'Customer segmentation and labeling successful.',
                'segment_summary': label_counts,
                'preview': preview
            })

        except Exception as e:
            return Response({'error': str(e)}, status=500)


class CustomerSegmentationView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            today = now().date()
            customers = Customer.objects.all()

            data = []
            for customer in customers:
                purchases = Purchase.objects.filter(customer=customer)

                if not purchases.exists():
                    continue  # Skip customers with no purchases

                total_spend = sum(p.total_amount for p in purchases)
                frequency = purchases.count()
                last_purchase_date = purchases.order_by('-purchase_date').first().purchase_date.date()
                recency = (today - last_purchase_date).days

                data.append({
                    'CustomerID': customer.id,
                    'TotalSpend': total_spend,
                    'PurchaseFrequency': frequency,
                    'LastPurchaseDays': recency
                })

            if not data:
                return Response({'error': 'No valid purchase data available.'}, status=404)

            df = pd.DataFrame(data)
            features = df[['TotalSpend', 'PurchaseFrequency', 'LastPurchaseDays']]
            kmeans = KMeans(n_clusters=3, random_state=42)
            df['Segment'] = kmeans.fit_predict(features)

            # Label segments
            segment_means = df.groupby('Segment')[['TotalSpend', 'PurchaseFrequency', 'LastPurchaseDays']].mean()
            labeled_segments = {}

            for segment_id in segment_means.index:
                spend = segment_means.loc[segment_id, 'TotalSpend']
                freq = segment_means.loc[segment_id, 'PurchaseFrequency']
                recency = segment_means.loc[segment_id, 'LastPurchaseDays']

                if spend > 800 and freq > 7 and recency < 10:
                    label = 'High Value'
                elif spend > 500 and freq > 4:
                    label = 'Mid-Tier'
                else:
                    label = 'At Risk'

                labeled_segments[segment_id] = label

            df['SegmentLabel'] = df['Segment'].map(labeled_segments)
            preview = df[['CustomerID', 'TotalSpend', 'PurchaseFrequency', 'LastPurchaseDays', 'SegmentLabel']].head(10).to_dict(orient='records')
            label_counts = df['SegmentLabel'].value_counts().to_dict()

            return Response({
                'message': 'Customer segmentation from database successful.',
                'segment_summary': label_counts,
                'preview': preview
            })

        except Exception as e:
            return Response({'error': str(e)}, status=500)


class UploadCSVView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj or not file_obj.name.endswith('.csv'):
            return Response({'error': 'Please upload a valid CSV file.'}, status=400)

        media_root = os.path.join(os.getcwd(), 'media')
        os.makedirs(media_root, exist_ok=True)

        # Generate unique file name
        file_ext = os.path.splitext(file_obj.name)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(media_root, unique_filename)

        with open(file_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        return Response({
            'message': 'File uploaded successfully.',
            'file_name': unique_filename
        })


# ------------------- Non-AI | direct tables' data for frontend  -------------------

class BasicAnalyticsOverview(APIView):
    def get(self, request, *args, **kwargs):
        try:
            total_customers = Customer.objects.count()
            total_products = Product.objects.count()
            total_purchases = Purchase.objects.count()
            total_revenue = Purchase.objects.aggregate(total=Sum('total_amount'))['total'] or 0

            top_categories = (
                PurchaseItem.objects
                .values('product__category')
                .annotate(quantity_sold=Sum('quantity'))
                .order_by('-quantity_sold')[:5]
            )

            top_customers = (
                Purchase.objects
                .values('customer__name')
                .annotate(total_spent=Sum('total_amount'))
                .order_by('-total_spent')[:5]
            )

            return Response({
                'summary': {
                    'total_customers': total_customers,
                    'total_products': total_products,
                    'total_purchases': total_purchases,
                    'total_revenue': float(total_revenue)
                },
                'top_categories': list(top_categories),
                'top_customers': list(top_customers)
            })

        except Exception as e:
            return Response({'error': str(e)}, status=500)

class CustomerListView(APIView):
    def get(self, request, *args, **kwargs):
        customers = Customer.objects.all().values(
            'id', 'name', 'gender', 'age', 'location', 'created_at'
        )
        data = [
            {
                **customer,
                'created_at': customer['created_at'].strftime('%Y-%m-%d %H:%M')
            } for customer in customers
        ]
        return Response(data)

class ProductListView(APIView):
    def get(self, request, *args, **kwargs):
        products = Product.objects.all().values(
            'id', 'name', 'category', 'price', 'base_price', 'stock_quantity'
        )
        return Response(list(products))

class PurchaseListView(APIView):
    def get(self, request, *args, **kwargs):
        purchases = Purchase.objects.select_related('customer').all()

        data = [
            {
                'id': purchase.id,
                'customer': purchase.customer.name or f"Customer {purchase.customer.id}",
                'purchase_date': purchase.purchase_date.strftime('%Y-%m-%d %H:%M'),
                'total_amount': float(purchase.total_amount),
                'discount_applied': purchase.discount_applied
            }
            for purchase in purchases
        ]
        return Response(data)
    
class PurchaseItemListView(APIView):
    def get(self, request, *args, **kwargs):
        items = PurchaseItem.objects.select_related('purchase', 'product').all()

        data = [
            {
                'id': item.id,
                'purchase_id': item.purchase.id,
                'product_name': item.product.name,
                'category': item.product.category,
                'quantity': item.quantity,
                'price_at_purchase': float(item.price_at_purchase),
                'purchase_date': item.purchase.purchase_date.strftime('%Y-%m-%d %H:%M'),
                'customer': item.purchase.customer.name or f"Customer {item.purchase.customer.id}"
            }
            for item in items
        ]
        return Response(data)


# ------------------ not applicable codes - reserved just in case ------------------
# return segmentation results without human-readable labels
# class CustomerSegmentationView(APIView):
#     def get(self, request, *args, **kwargs):
#         file_name = request.query_params.get('file')
#         if not file_name:
#             return Response({'error': 'Missing "file" query parameter.'}, status=400)

#         file_path = os.path.join(os.getcwd(), 'media', file_name)
#         if not os.path.exists(file_path):
#             return Response({'error': f'File "{file_name}" not found.'}, status=404)

#         try:
#             df = pd.read_csv(file_path)
#             required_columns = ['CustomerID', 'TotalSpend', 'PurchaseFrequency', 'LastPurchaseDays']
#             if not all(col in df.columns for col in required_columns):
#                 return Response({'error': f'Missing required columns: {required_columns}'}, status=400)

#             features = df[['TotalSpend', 'PurchaseFrequency', 'LastPurchaseDays']]
#             kmeans = KMeans(n_clusters=3, random_state=42)
#             df['Segment'] = kmeans.fit_predict(features)

#             preview = df[['CustomerID', 'TotalSpend', 'PurchaseFrequency', 'LastPurchaseDays', 'Segment']].head(10).to_dict(orient='records')
#             segment_counts = df['Segment'].value_counts().to_dict()

#             return Response({
#                 'message': 'Customer segmentation successful.',
#                 'segments': segment_counts,
#                 'preview': preview
#             })

#         except Exception as e:
#             return Response({'error': str(e)}, status=500)


# csv file upload without renaming unique file name
# class UploadCSVView(APIView):
#     parser_classes = [MultiPartParser]

#     def post(self, request, *args, **kwargs):
#         file_obj = request.FILES.get('file')

#         if not file_obj or not file_obj.name.endswith('.csv'):
#             return Response({'error': 'Please upload a valid CSV file.'}, status=400)

#         # Save the uploaded file to the media directory
#         media_root = os.path.join(os.getcwd(), 'media')
#         os.makedirs(media_root, exist_ok=True)

#         file_path = os.path.join(media_root, file_obj.name)
#         with open(file_path, 'wb+') as destination:
#             for chunk in file_obj.chunks():
#                 destination.write(chunk)

#         return Response({'message': 'File uploaded successfully.'})
    
#         # Read and preview file with pandas
#         # try:
#         #     df = pd.read_csv(file_path)
#         #     preview = df.head(5).to_dict(orient='records')
#         # except Exception as e:
#         #     return Response({'error': f'Failed to read CSV: {str(e)}'}, status=500)

#         # return Response({
#         #     'message': 'File uploaded and read successfully.',
#         #     'preview': preview,
#         #     'columns': list(df.columns),
#         #     'row_count': len(df)
#         # })

