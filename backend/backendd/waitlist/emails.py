import base64
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


LOGO_PATH = Path(__file__).parent / "assets" / "dumosense-logo.png"


def build_confirmation_email(registration):
    first_name = registration.full_name.split()[0]
    escaped_first_name = escape(first_name)
    website_url = settings.WAITLIST_WEBSITE_URL.rstrip("/")
    subject = "Congratulations! You're on the DumoSense Waitlist 🎉"
    text = (
        f"Hi {first_name},\n\n"
        "Congratulations! You're officially on the DumoSense Early Access Waitlist.\n\n"
        "Thank you for joining us as we build a smarter future for health and wellbeing. "
        "As part of our early access community, you'll be among the first to receive updates "
        "about MindGuard, Health Reserve, product launches, and exclusive testing opportunities.\n\n"
        "We're excited to have you with us.\n\n"
        "Your Wellbeing Deserves a Smarter Future.\n\n"
        "Warm regards,\n"
        "The DumoSense Team"
    )
    html = (
        '<div style="margin:0;background:#f8f3f5;padding:32px 16px;font-family:Arial,sans-serif;color:#2c1723">'
        '<div style="max-width:600px;margin:0 auto;background:#fff;border:1px solid #eadfe4;border-radius:20px;overflow:hidden">'
        '<div style="padding:28px 32px;background:#5a3045;text-align:center">'
        f'<a href="{website_url}" style="text-decoration:none"><img src="cid:dumosense-logo" alt="DumoSense" width="188" style="display:block;width:188px;height:auto;margin:0 auto;border:0"></a>'
        '</div><div style="padding:32px">'
        f'<p style="font-size:16px;line-height:1.6">Hi {escaped_first_name},</p>'
        '<h1 style="margin:20px 0 12px;color:#5a3045;font-size:26px;line-height:1.25">Congratulations! 🎉</h1>'
        '<p style="font-size:16px;line-height:1.6"><strong>You’re officially on the DumoSense Early Access Waitlist.</strong></p>'
        '<p style="font-size:15px;line-height:1.7;color:#6b5260">Thank you for joining us as we build a smarter future for health and wellbeing. As part of our early access community, you’ll be among the first to receive updates about MindGuard, Health Reserve, product launches, and exclusive testing opportunities.</p>'
        '<p style="font-size:15px;line-height:1.7;color:#6b5260">We’re excited to have you with us.</p>'
        '<p style="margin:24px 0;color:#5a3045;font-size:17px;font-weight:bold">Your Wellbeing Deserves a Smarter Future.</p>'
        '<p style="font-size:15px;line-height:1.6">Warm regards,<br><strong>The DumoSense Team</strong></p>'
        f'<p style="margin-top:28px"><a href="{website_url}" style="display:inline-block;padding:12px 20px;background:#5a3045;color:#fff;text-decoration:none;border-radius:24px;font-size:14px;font-weight:bold">Visit DumoSense</a></p>'
        '</div><div style="padding:18px 32px;background:#f8f3f5;color:#8a6678;text-align:center;font-size:12px">DumoSense — Your Wellbeing Deserves a Smarter Future.</div>'
        '</div></div>'
    )
    message = EmailMultiAlternatives(
        subject,
        text,
        from_email=f"{settings.WAITLIST_FROM_NAME} <{settings.WAITLIST_FROM_EMAIL}>",
        to=[registration.email],
    )
    message.attach_alternative(html, "text/html")
    message.resend_attachments = [
        {
            "filename": LOGO_PATH.name,
            "content": base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii"),
            "content_id": "dumosense-logo",
            "content_type": "image/png",
        }
    ]
    message.resend_idempotency_key = f"waitlist-confirmation/{registration.pk}"
    return message
