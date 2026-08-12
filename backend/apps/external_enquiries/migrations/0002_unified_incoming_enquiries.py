import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def seed_source_history(apps, _schema_editor):
    Submission = apps.get_model("external_enquiries", "ExternalEnquirySubmission")
    SourceEvent = apps.get_model("external_enquiries", "IncomingEnquirySourceEvent")
    SourceEvent.objects.bulk_create(
        [
            SourceEvent(
                submission=submission,
                channel=submission.channel,
                source_reference=submission.external_submission_id,
                original_message=submission.message,
                metadata={"source_type": submission.source_type},
            )
            for submission in Submission.objects.iterator()
        ]
    )


def remove_source_history(apps, _schema_editor):
    apps.get_model("external_enquiries", "IncomingEnquirySourceEvent").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("external_enquiries", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="externalenquirysubmission",
            name="captured_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="captured_incoming_enquiries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="externalenquirysubmission",
            name="channel",
            field=models.CharField(
                choices=[
                    ("WEBSITE", "Website"),
                    ("TRADEINDIA", "TradeIndia"),
                    ("WHATSAPP", "WhatsApp"),
                    ("PHONE", "Phone"),
                    ("EMAIL", "Email"),
                    ("IN_PERSON", "In person"),
                    ("MANUAL", "Manual"),
                    ("OTHER", "Other"),
                ],
                default="WEBSITE",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="externalenquirysubmission",
            name="credential",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="submissions",
                to="external_enquiries.integrationcredential",
            ),
        ),
        migrations.AlterField(
            model_name="externalenquirysubmission",
            name="idempotency_key",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AlterField(
            model_name="externalenquirysubmission",
            name="payload_checksum",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AlterField(
            model_name="externalenquirysubmission",
            name="request_id",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AlterField(
            model_name="externalenquirysubmission",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("CONTACT_FORM", "Contact form"),
                    ("PRODUCT_QUOTE", "Product request quote"),
                    ("CAMPAIGN", "Campaign form"),
                    ("MARKETPLACE", "Marketplace enquiry"),
                    ("CHAT", "Chat message"),
                    ("PHONE_CALL", "Phone call"),
                    ("EMAIL_MESSAGE", "Email message"),
                    ("IN_PERSON", "In-person conversation"),
                    ("MANUAL_ENTRY", "Manual entry"),
                    ("OTHER", "Other"),
                ],
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="IncomingEnquirySourceEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "channel",
                    models.CharField(
                        choices=[
                            ("WEBSITE", "Website"),
                            ("TRADEINDIA", "TradeIndia"),
                            ("WHATSAPP", "WhatsApp"),
                            ("PHONE", "Phone"),
                            ("EMAIL", "Email"),
                            ("IN_PERSON", "In person"),
                            ("MANUAL", "Manual"),
                            ("OTHER", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("source_reference", models.CharField(blank=True, max_length=250)),
                ("original_message", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "captured_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="incoming_enquiry_source_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="source_history",
                        to="external_enquiries.externalenquirysubmission",
                    ),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.RunPython(seed_source_history, remove_source_history),
    ]
