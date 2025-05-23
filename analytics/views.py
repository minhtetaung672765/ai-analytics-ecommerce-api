# from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
import pandas as pd
import os
import uuid

from sklearn.cluster import KMeans

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

class CustomerSegmentationView(APIView):
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

