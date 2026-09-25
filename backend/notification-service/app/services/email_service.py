import aiosmtplib
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta
from app.config import settings

def format_vietnam_time(time_val):
    if not time_val:
        return ""
    if isinstance(time_val, str):
        try:
            dt = datetime.fromisoformat(time_val.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = datetime.strptime(time_val, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return time_val
    elif isinstance(time_val, datetime):
        dt = time_val
    else:
        return str(time_val)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    vn_tz = timezone(timedelta(hours=7))
    vn_time = dt.astimezone(vn_tz)
    return vn_time.strftime("%d/%m/%Y %H:%M:%S")

async def send_email(to_email: str, subject: str, html_content: str):
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"\n[DEMO NOTIFICATION] Cần gửi email tới: {to_email}")
        print(f"Tiêu đề: {subject}")
        print(f"Nội dung: {html_content}\n")
        return

    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(html_content, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        start_tls=True,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
    )

async def send_otp_email(to_email: str, otp: str, expires_in_minutes: int):
    subject = f"[{otp}] Mã xác thực giao dịch iBanking"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2>Xác thực giao dịch thanh toán học phí</h2>
        <p>Mã OTP của bạn là:</p>
        <div style="font-size: 28px; font-weight: bold; color: #2563eb; letter-spacing: 4px; padding: 10px 0;">
            {otp}
        </div>
        <p>Mã này có hiệu lực trong vòng <strong>{expires_in_minutes} phút</strong>.</p>
        <p style="color: #666; font-size: 13px;">Vui lòng không chia sẻ mã này cho bất kỳ ai.</p>
    </div>
    """
    await send_email(to_email, subject, html_content)

async def send_receipt_email(to_email: str, data: dict):
    subject = f"Biên lai thanh toán học phí thành công - {data['transaction_id']}"
    amount_str = f"{data['amount']:,.0f} đ".replace(",", ".")
    created_at_vn = format_vietnam_time(data.get("created_at"))

    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2 style="color: #16a34a;">Thanh toán học phí thành công</h2>
        <p>Cảm ơn bạn đã sử dụng dịch vụ iBanking. Dưới đây là chi tiết giao dịch:</p>
        <table style="width: 100%; max-width: 500px; border-collapse: collapse; margin-top: 15px;">
            <tr><td style="padding: 8px 0; color: #666;">Mã giao dịch:</td><td><strong>{data['transaction_id']}</strong></td></tr>
            <tr><td style="padding: 8px 0; color: #666;">Mã số sinh viên:</td><td><strong>{data['student_code']}</strong></td></tr>
            <tr><td style="padding: 8px 0; color: #666;">Tên sinh viên:</td><td><strong>{data['student_name']}</strong></td></tr>
            <tr><td style="padding: 8px 0; color: #666;">Số tiền:</td><td><strong style="color: #2563eb;">{amount_str}</strong></td></tr>
            <tr><td style="padding: 8px 0; color: #666;">Thời gian:</td><td>{created_at_vn}</td></tr>
        </table>
    </div>
    """
    await send_email(to_email, subject, html_content)