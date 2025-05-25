from django.core.management.base import BaseCommand
from analytics.models import Customer, Product, Purchase, PurchaseItem
from faker import Faker
import random
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seed the database with realistic test data'

    def handle(self, *args, **kwargs):
        fake = Faker()
        self.stdout.write("🧹 Clearing existing data...")
        PurchaseItem.objects.all().delete()
        Purchase.objects.all().delete()
        Product.objects.all().delete()
        Customer.objects.all().delete()

        self.stdout.write("👥 Creating customers...")
        customers = []
        for _ in range(30):
            gender = random.choice(['Male', 'Female'])
            age = random.randint(18, 65)
            name = fake.name_male() if gender == 'Male' else fake.name_female()
            location = fake.city()
            customer = Customer.objects.create(
                name=name,
                gender=gender,
                age=age,
                location=location
            )
            customers.append(customer)

        self.stdout.write("📦 Creating products...")
        categories = ['Clothing', 'Footwear', 'Accessories']
        products = []
        for _ in range(10):
            base_price = Decimal(random.randint(20, 200))
            markup = Decimal(random.uniform(1.1, 1.5))  # 10% to 50% markup
            final_price = (base_price * markup).quantize(Decimal('0.01'))
            product = Product.objects.create(
                name=fake.word().capitalize() + ' ' + random.choice(['Delux', 'Pro', 'Lux', 'Devine', 'Aes', 'X']),
                category=random.choice(categories),
                base_price=base_price,
                price=final_price,
                stock_quantity=random.randint(20, 100)
            )
            products.append(product)

        self.stdout.write("🧾 Creating purchases and items...")
        for _ in range(50):
            customer = random.choice(customers)
            purchase_date = timezone.now() - timedelta(days=random.randint(1, 90))
            discount_applied = random.choice([True, False])

            purchase = Purchase.objects.create(
                customer=customer,
                purchase_date=purchase_date,
                total_amount=Decimal('0.00'),  # will be updated
                discount_applied=discount_applied
            )

            num_items = random.randint(1, 4)
            total = Decimal('0.00')
            for _ in range(num_items):
                product = random.choice(products)
                quantity = random.randint(1, 3)
                price = product.price
                subtotal = (price * quantity).quantize(Decimal('0.01'))

                PurchaseItem.objects.create(
                    purchase=purchase,
                    product=product,
                    quantity=quantity,
                    price_at_purchase=price
                )

                total += subtotal

            purchase.total_amount = total
            purchase.save()

        self.stdout.write(self.style.SUCCESS("✅ Database seeding completed successfully."))
