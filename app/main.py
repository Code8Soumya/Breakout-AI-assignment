import logging
import os
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from helper import get_dynamodb_table, check_user_exists, save_chat_in_user_table, create_telegram_app


# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,  # Change to DEBUG for more detailed logs
    handlers=[
        logging.FileHandler("logs/bot.log"),  # Save logs to 'bot.log'
        logging.StreamHandler()  # Continue showing logs in the console
    ]
)
logger = logging.getLogger(__name__)

table = get_dynamodb_table()

# Define the start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message with a contact button."""
    try:
        user_id = update.effective_user.id
        # Check if user already exists
        if check_user_exists(table, user_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Welcome back! Nice to see you again."
            )
            return

        # For new users, create a contact request button
        contact_button = KeyboardButton("Share Phone Number", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please share your phone number to proceed.",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, something went wrong. Please try again later."
        )
        
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the user's phone number in MongoDB and send a confirmation message."""
    try:
        if update.message.contact:
            phone_number = update.message.contact.phone_number
            user_id = update.effective_user.id
            username = update.effective_user.username
            first_name = update.effective_user.first_name        
            # Save user data to DynamoDB
            save_chat_in_user_table(
                table=table,
                user_id=user_id,
                phone_number=phone_number,
                first_name=first_name,
                user_name=username,
                message=('user', 'Shared contact info'),
                message_type='contact',
            )

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Thank you, {first_name}! Your contact info has been saved.",
                reply_markup=ReplyKeyboardRemove(),
            )

    except Exception as e:
        logger.error(f"Error handling contact: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="An error occurred while saving your phone number."
        )
# Define the echo handler
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        user_message = update.message.text
        # phone_number = update.effective_user.contact.phone_number if update.effective_user.contact else None
        first_name = update.effective_user.first_name
        username = update.effective_user.username
        logger.info(f"Received message from user {user_id}: {user_message}")
        
        # Save user message
        save_chat_in_user_table(
            table=table,
            user_id=user_id,
            # phone_number=99,
            # first_name=first_name, 
            # user_name=username,
            message=('user', user_message),
            message_type='text'
        )
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=user_message
        )
        
        # Save bot response
        save_chat_in_user_table(
            table=table,
            user_id=user_id,
            # phone_number=99,
            # first_name=first_name,
            # user_name=username, 
            message=('bot', user_message),
            message_type='text'
        )
        
    except Exception as e:
        logger.error(f"Error in echo handler: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Sorry, something went wrong. Please try again later."
        )
        
        
if __name__ == '__main__':
    # Initialize the application
    application = create_telegram_app()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))
    
    # Log startup information
    logger.info("Bot is starting...")
    application.run_polling()

