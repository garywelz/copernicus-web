import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from datetime import datetime

class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv("NOTIFICATION_EMAIL", "garywelz@gmail.com")
        self.sender_password = os.getenv("NOTIFICATION_EMAIL_PASSWORD")
        
    async def send_podcast_completion_email(
        self, 
        recipient_email: str, 
        job_id: str, 
        podcast_title: str, 
        topic: str, 
        audio_url: str,
        duration: str,
        canonical_filename: str
    ) -> bool:
        """Send email notification when podcast generation is complete"""
        
        if not self.sender_password:
            print("⚠️  Email password not configured. Skipping email notification.")
            return False
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"🎙️ Your Copernicus Podcast is Ready: {podcast_title}"
            
            # Create HTML body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #2c3e50; margin-bottom: 10px;">🎙️ Copernicus Podcast Ready!</h1>
                        <p style="color: #7f8c8d; font-size: 18px;">Your AI-generated research podcast is complete</p>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <h2 style="color: #2c3e50; margin-top: 0;">📋 Podcast Details</h2>
                        <p><strong>Title:</strong> {podcast_title}</p>
                        <p><strong>Topic:</strong> {topic}</p>
                        <p><strong>Duration:</strong> {duration}</p>
                        <p><strong>Job ID:</strong> {job_id}</p>
                        <p><strong>Filename:</strong> {canonical_filename}</p>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{audio_url}" 
                           style="background: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                            🎧 Listen to Podcast
                        </a>
                    </div>
                    
                    <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin-top: 20px;">
                        <p style="margin: 0; color: #27ae60;">
                            <strong>✅ Generation Complete:</strong> Your podcast has been successfully generated and is ready for listening.
                        </p>
                    </div>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 14px; color: #7f8c8d;">
                        <p>Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')}</p>
                        <p>This is an automated notification from the Copernicus AI Podcast Generator.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Create server connection and send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                
            print(f"✅ Email notification sent to {recipient_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email notification: {e}")
            return False
    
    async def send_podcast_failure_email(
        self, 
        recipient_email: str, 
        job_id: str, 
        topic: str, 
        error_message: str
    ) -> bool:
        """Send email notification when podcast generation fails"""
        
        if not self.sender_password:
            print("⚠️  Email password not configured. Skipping failure email notification.")
            return False
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"❌ Podcast Generation Failed: {topic}"
            
            # Create HTML body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #e74c3c; margin-bottom: 10px;">❌ Generation Failed</h1>
                        <p style="color: #7f8c8d; font-size: 18px;">Your podcast generation encountered an error</p>
                    </div>
                    
                    <div style="background: #fdf2f2; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #e74c3c;">
                        <h2 style="color: #2c3e50; margin-top: 0;">📋 Error Details</h2>
                        <p><strong>Topic:</strong> {topic}</p>
                        <p><strong>Job ID:</strong> {job_id}</p>
                        <p><strong>Error:</strong> {error_message}</p>
                    </div>
                    
                    <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px;">
                        <p style="margin: 0; color: #856404;">
                            <strong>⚠️ What to do:</strong> Please try generating the podcast again, or contact support if the issue persists.
                        </p>
                    </div>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 14px; color: #7f8c8d;">
                        <p>Error occurred on: {datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')}</p>
                        <p>This is an automated notification from the Copernicus AI Podcast Generator.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Create server connection and send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                
            print(f"✅ Failure email notification sent to {recipient_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send failure email notification: {e}")
            return False
