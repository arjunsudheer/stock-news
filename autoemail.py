import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv
import os
import markdown
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class StockRecommendationEmailer:
    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Get email configuration with validation
        self.sender_email = os.getenv("SENDER_EMAIL")
        if not self.sender_email:
            raise ValueError("SENDER_EMAIL not found in environment variables")

        self.sender_password = os.getenv("SENDER_PASSWORD")
        if not self.sender_password:
            raise ValueError("SENDER_PASSWORD not found in environment variables")

        self.smtp_server = os.getenv("SMTP_SERVER")
        if not self.smtp_server:
            raise ValueError("SMTP_SERVER not found in environment variables")

        self.smtp_port = os.getenv("SMTP_PORT")
        if not self.smtp_port:
            raise ValueError("SMTP_PORT not found in environment variables")
        self.smtp_port = int(self.smtp_port)

        recipient_emails = os.getenv("RECIPIENT_EMAILS")
        if not recipient_emails:
            raise ValueError("RECIPIENT_EMAILS not found in environment variables")
        self.recipient_emails = [email.strip() for email in recipient_emails.split(",")]

    def format_email_content(self, stock_analyses: Dict[str, str]) -> str:
        """
        Format multiple stock analyses into one email
        """
        stock_analyses_html = ""
        for symbol, analysis in stock_analyses.items():
            if not symbol:
                raise ValueError("Stock symbol is empty")

            stock_analyses_html += f"""
                <div class="stock-analysis" style="margin-bottom: 30px; border-bottom: 1px solid #ccc; padding-bottom: 20px;">
                    <h2>Analysis for {symbol}</h2>
                    <div style="margin: 15px 0;">
                        {markdown.markdown(analysis)}
                    </div>
                </div>
            """

        html_content = f"""
        <html>
            <body>
                <h2>Stock Analysis Report - {datetime.now().strftime('%Y-%m-%d')}</h2>
                
                {stock_analyses_html}
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    This is an automated stock analysis report. Please do your own research before making investment decisions.
                </p>
            </body>
        </html>
        """

        return html_content

    def send_email(self, stock_analyses: Dict[str, str]) -> bool:
        """
        Send email with multiple stock analyses results.
        The stock_analyses dictionary contains stock symbols as keys and their analysis summaries as values.
        """
        try:
            # Validate input data
            if not stock_analyses:
                raise ValueError("No analyses provided")

            for symbol in stock_analyses.keys():
                if not stock_analyses[symbol]:
                    stock_analyses[symbol] = "No analysis available."

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = (
                f"Stock Analysis Report - {datetime.now().strftime('%Y-%m-%d')}"
            )
            msg["From"] = self.sender_email
            msg["To"] = ", ".join(self.recipient_emails)

            # Create HTML content
            html_content = self.format_email_content(stock_analyses)
            msg.attach(MIMEText(html_content, "html"))

            # Connect to SMTP server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            return True

        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            return False
        except smtplib.SMTPAuthenticationError:
            logger.error(
                "SMTP Authentication failed. Please check your email and password."
            )
            return False
        except smtplib.SMTPException as se:
            logger.error(f"SMTP error occurred: {str(se)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}", exc_info=True)
            return False
