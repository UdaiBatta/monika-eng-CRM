from django.db import migrations


FEATURES = {
    "quick_quotation": "Allow permitted Sales employees to start a quotation without an approved estimate.",
    "website_enquiries": "Receive and review quotation requests submitted from the company website.",
}


def seed_existing_companies(apps, schema_editor):
    company_model = apps.get_model("organization", "Company")
    feature_flag = apps.get_model("configuration", "FeatureFlag")
    for company in company_model.objects.all():
        for key, description in FEATURES.items():
            feature_flag.objects.get_or_create(
                company=company,
                key=key,
                defaults={"description": description, "is_enabled": True},
            )


def remove_seeded_features(apps, schema_editor):
    apps.get_model("configuration", "FeatureFlag").objects.filter(key__in=FEATURES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0002_companysettings_record_version_and_more"),
        ("organization", "0002_branch_record_version_company_record_version_and_more"),
    ]
    operations = [migrations.RunPython(seed_existing_companies, remove_seeded_features)]

