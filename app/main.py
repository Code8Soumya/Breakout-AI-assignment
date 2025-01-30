# Import required libraries
import base64
from langchain_core.messages import HumanMessage
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import filters, MessageHandler, CommandHandler, ContextTypes
from helper import (
    get_dynamodb_table, 
    check_user_exists,
    save_chat_in_user_table,
    create_telegram_app,
    save_and_cache_messages,
    setup_logging
)
from agents import initialize_llm, search_crew

prompt_template = """ 
    You are a friendly and engaging assistant. Please respond to the following message in an informative yet conversational manner.  

    - Use relevant emojis to enhance engagement and clarity. 😊🎯  
    - Proactively ask follow-up questions when necessary. 🤔💡  
    - Adapt your tone based on the user's context and mood. 🚀  

    Message: {message}  
    """

# Initialize logging, database and LLM
logger = setup_logging()
table = get_dynamodb_table()
llm = initialize_llm()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command.
    If user exists, send welcome back message.
    If new user, request phone number via contact button.
    """
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
    """
    Handle user contact sharing.
    Save user details to DynamoDB when contact is shared.
    """
    try:
        if update.message.contact:
            # Extract user details
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

async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle text messages from user.
    Process message through LLM and return response.
    """
    try:
        user_id = update.effective_user.id
        
        # Verify user registration
        if not check_user_exists(table, user_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please use /start to proceed and share your contact info.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return
        
        # Process user message
        user_message = update.message.text
        context_msgs = save_and_cache_messages(
            table=table,
            user_id=user_id,
            msg=user_message,
            msg_type='text',
            role='human',
        )

        formatted_prompt = prompt_template.format(message=context_msgs)
        llm_response = llm.invoke(formatted_prompt).content
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=llm_response,
        )
        
        # Save assistant response
        save_and_cache_messages(
            table=table,
            user_id=user_id,
            msg=llm_response,
            msg_type='text',
            role='assistant',
        )
        
    except Exception as e:
        logger.error(f"Error in message handler: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, something went wrong. Please try again later.",
        )
        
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle photo messages from user.
    Process image through LLM for description.
    """
    try:
        user_id = update.effective_user.id
        
        # Verify user registration
        if not check_user_exists(table, user_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please use /start to proceed and share your contact info.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        # Save image message
        save_and_cache_messages(
            table=table,
            user_id=user_id,
            msg='a image',
            msg_type='image',
            role='human',
        )

        # Process image
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        photo = base64.b64encode(photo_bytes).decode("utf-8")
        
        # Create message for image analysis
        message = HumanMessage(
            content = [
                {"type": "text", "text": "Describe the content of this image"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{photo}"},
                },
            ]
        )
        
        # Get image description from LLM
        llm_response = llm.invoke([message]).content
                
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=llm_response,
        )
        
        # Save assistant response
        save_and_cache_messages(
            table=table,
            user_id=user_id,
            msg=llm_response,
            msg_type='text',
            role='assistant',
        )

    except Exception as e:
        logger.error(f"Error in photo handler: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, something went wrong. Please try again later.",
        )
        
async def web_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle web search command and query.
    Search web for query and return results.
    """
    try:
        user_id = update.effective_user.id
        
        # Verify user registration
        if not check_user_exists(table, user_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please use /start to proceed and share your contact info.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        # Verify search query exists
        if not context.args:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please provide a search query after /web_search command"
            )
            return

        # Process search query
        search_query = ' '.join(context.args)
        
        save_and_cache_messages(
            table=table,
            user_id=user_id,
            msg=search_query,
            msg_type='web search query',
            role='human',
        )

        # Get search results
        search_result = search_crew.kickoff(inputs={'topic': search_query})

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=search_result
        )

        # Save search results
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

# Main execution block        
if __name__ == '__main__':
    # Initialize Telegram application
    application = create_telegram_app()
    
    # Register command and message handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('search', web_search))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), msg_handler))
    application.add_handler(MessageHandler(filters.PHOTO & (~filters.COMMAND), photo_handler))
            
    logger.info("Bot is starting...")
    application.run_polling()

