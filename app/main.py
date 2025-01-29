import logging
from io import BytesIO
import base64
from langchain_core.messages import HumanMessage
from telegram import Update
from telegram.ext import filters, MessageHandler, CommandHandler, ContextTypes
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from helper import get_dynamodb_table, check_user_exists, save_chat_in_user_table, create_telegram_app, save_and_cache_messages, setup_logging
from agents import initialize_llm, search_crew

logger = setup_logging()
table = get_dynamodb_table()
llm = initialize_llm()

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
            text="An error occurred while saving your phone number.",
        )
# Define the echo handler
async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        if check_user_exists(table, user_id) == False:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please use /start to proceed and share your contact info.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return
        
        user_message = update.message.text
        context_msgs = save_and_cache_messages(
            table=table,
            user_id=user_id,
            msg=user_message,
            msg_type='text',
            role='human',
        )

        llm_response = llm.invoke(context_msgs).content
    
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=llm_response,
        )
        save_and_cache_messages(
            table=table,
            user_id=user_id,
            msg=llm_response,
            msg_type='text',
            role='assistant',
        )
        
    except Exception as e:
        logger.error(f"Error in echo handler: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, something went wrong. Please try again later.",
        )
        
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        if check_user_exists(table, user_id) == False:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please use /start to proceed and share your contact info.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        save_and_cache_messages(
            table=table,
            user_id=user_id,
            msg='a image',
            msg_type='image',
            role='human',
        )

        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        photo = base64.b64encode(photo_bytes).decode("utf-8")
        
        message = HumanMessage(
            content = [
                {"type": "text", "text": "Describe the content of this image"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{photo}"},
                },
            ]
        )
        
        llm_response = llm.invoke([message]).content
                
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=llm_response,
        )
        
        save_and_cache_messages(
            table=table,
            user_id=user_id,
            msg=llm_response,
            msg_type='text',
            role='assistant',
        )

    except Exception as e:
        logger.error(f"Error in echo handler: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, something went wrong. Please try again later.",
        )
        
        
async def web_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle web search command and query"""
    try:
        user_id = update.effective_user.id
        if check_user_exists(table, user_id) == False:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please use /start to proceed and share your contact info.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        if not context.args:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please provide a search query after /web_search command"
            )
            return

        search_query = ' '.join(context.args)
        
        save_and_cache_messages(
            table=table,
            user_id=user_id,
            msg=search_query,
            msg_type='web search query',
            role='human',
        )

        search_result = search_crew.kickoff(inputs={'topic': search_query})

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=search_result
        )

        save_and_cache_messages(
            table=table,
            user_id=user_id,
            msg=search_result,
            msg_type='web search result', 
            role='assistant',
        )

    except Exception as e:
        logger.error(f"Error in web search handler: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, something went wrong with the web search. Please try again later."
        )
        
if __name__ == '__main__':
    application = create_telegram_app()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('search', web_search))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), msg_handler))
    application.add_handler(MessageHandler(filters.PHOTO & (~filters.COMMAND), photo_handler))
    # application.add_handler(MessageHandler(filters.Document.ALL & (~filters.COMMAND), document_handler))
            
    logger.info("Bot is starting...")
    application.run_polling()

