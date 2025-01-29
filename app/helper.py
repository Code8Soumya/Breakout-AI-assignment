from datetime import datetime
from telegram.ext import ApplicationBuilder
from cachetools import LRUCache
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.tools import tool
import boto3
import logging
import os
from dotenv import load_dotenv
load_dotenv()

def setup_logging():
    try:
        os.makedirs("logs", exist_ok=True)
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.ERROR,
            handlers=[
                logging.FileHandler("logs/bot.log"),
            ]
        )
        logger = logging.getLogger(__name__)
        return logger
    except Exception as e:
        print(f"Error setting up logging: {str(e)}")


logger = setup_logging()

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
        return True if 'Item' in response else False
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

user_cache = LRUCache(maxsize=128)

def get_formatted_messages(table, user_id, num_msgs=50):
    try:
        # Get user item from DynamoDB
        # if user_id in user_cache:
        #     return user_cache[user_id]
        
        response = table.get_item(
            Key={
                'user_id': user_id
            }
        )
        
        # Check if user exists and has chat history
        if 'Item' not in response or 'chats' not in response['Item']:
            return []
            
        # Get chat history
        chats = response['Item']['chats']
        recent_chats = chats[-num_msgs:] if len(chats) > num_msgs else chats
        
        # Format messages as (role, content) tuples
        formatted_msgs = []
        for chat in recent_chats:
            role = chat['from']
            formatted_msgs.append((role, chat['message']))
        
        user_cache[user_id] = formatted_msgs
        return user_cache[user_id]
        
    except Exception as e:
        logger.error(f"Error occurred in app/helper.py in get_formatted_messages: {str(e)}")
        return []


def save_and_cache_messages(table, user_id, msg, msg_type, role):
    try:
        save_chat_in_user_table(
            table=table,
            user_id=user_id, 
            message=(role, msg),
            message_type=msg_type,
        )
        
        if user_id in user_cache:
            cache = user_cache[user_id]
            cache.append((role, msg))
            if len(cache) > 20:
                cache.pop(0)
            user_cache[user_id] = cache
        else:
            get_formatted_messages(table, user_id)
            
        return user_cache[user_id]
    
    except Exception as e:
        logger.error(f"Error occurred in save_and_cache_messages for user {user_id}: {str(e)}")
        return []    

class TavilySearchTool:
    @tool('Search Internet')
    def search_internet(query: str) -> str:
        """This tool accepts only one parameter named 'query' and is
        useful to search the internet about a given query and return relevant results."""
        try:
            tavily_tool = TavilySearchResults(
                max_results = 5,
                search_depth = "advanced", 
                include_answer = False,
                include_raw_content = False,
                include_images = False,
            )
            results = tavily_tool.invoke(query)
            content = "\n\n".join([f"{i['url']} + {i['content']}" for i in results])
            return content
        except Exception as e:
            logger.error(f"Error occurred in TavilySearchTool.search_internet: {str(e)}")    