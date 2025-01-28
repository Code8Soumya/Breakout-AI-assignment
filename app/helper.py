from datetime import datetime
from telegram.ext import ApplicationBuilder
import logging
import boto3
import os
from dotenv import load_dotenv

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/helper.log"),
    ]
)
logger = logging.getLogger(__name__)

def get_dynamodb_table():
    try:
        load_dotenv()
        dynamodb = boto3.resource(
            'dynamodb',
            region_name = 'ap-south-1',  # Replace with your desired region
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID'),  # Optional if using ~/.aws/credentials
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY'),  # Optional if using ~/.aws/credentials
        )
        table = dynamodb.Table('telebot_users')
        return table
    except Exception as e:
        logger.error(f"Error occurred in app/helper.py in get_dynamodb_table: {str(e)}")
        return None    

def check_user_exists(table, user_id):
    try:
        response = table.get_item(
            Key={
                'user_id': user_id
            }
        )
        return 'Item' in response
    except Exception as e:
        logger.error(f"Error occurred in app/helper.py in check_user_exists: {str(e)}")
        return False 

def save_chat_in_user_table(table, user_id, message, phone_number='', first_name='', user_name='', message_type = 'text'):
    try:
        table.update_item(
            Key={'user_id': user_id},
            UpdateExpression=(
                "SET "
                "phone_number = if_not_exists(phone_number, :phone_number), "
                "first_name = if_not_exists(first_name, :first_name), "
                "user_name = if_not_exists(user_name, :user_name), "
                "chats = list_append(if_not_exists(chats, :empty_list), :new_chat)"
            ),
            ExpressionAttributeValues={
                ':phone_number': phone_number,
                ':first_name': first_name,
                ':user_name': user_name,
                ':empty_list': [],
                ':new_chat': [{
                    'from': message[0],
                    'message': message[1],
                    'message_type': message_type,
                    'timestamp': datetime.now().isoformat()
                }]
            }
        )
    except Exception as e:
        logger.error(f"Error occurred in app/helper.py in save_chat_in_user_table: {str(e)}")

def create_telegram_app():
    try:
        load_dotenv()
        application = ApplicationBuilder().token(os.getenv("telebot_token")).build()
        return application
    except Exception as e:
        logger.error(f"Error occurred in app/helper.py in create_telegram_app: {str(e)}")
        return None       
