import os
from datetime import datetime
from bot.clients import bot, BOT_INFO, store
from bot.config import COMMIT_SHA, HF_SPACE_ID, HOSTING_LABEL, MODEL, RATE_LIMIT
from bot.ai import ask_ai
from bot.helpers import is_allowed, keep_typing, send_reply, should_respond
from bot.history import clear_history
from bot.preferences import get_provider, set_provider
from bot.rate_limit import is_rate_limited

# Verbose console logging for local dev and teaching. Enabled by
# BOT_VERBOSE_LOG=1 (run_local.py sets this automatically). Prints one
# line per inbound/outbound message so kids and teachers can see the
# conversation flow in their terminal while the bot is running.
VERBOSE_LOG = os.environ.get("BOT_VERBOSE_LOG", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def _log(message, direction: str, text: str) -> None:
    """Print a one-line trace of a message in verbose mode.

    direction is "in" (user → bot) or "out" (bot → user). Text is
    truncated to 500 characters so long AI replies don't flood the
    terminal. Newlines are collapsed for single-line readability.
    """
    if not VERBOSE_LOG:
        return
    user = message.from_user
    user_name = (
        f"@{user.username}" if user.username else (user.first_name or f"user:{user.id}")
    )
    bot_name = f"@{BOT_INFO.username}"
    snippet = (text or "").replace("\n", " ").replace("\r", " ")
    if len(snippet) > 500:
        snippet = snippet[:500] + "..."
    if direction == "in":
        sender, receiver = user_name, bot_name
    else:
        sender, receiver = bot_name, user_name
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {sender} → {receiver}: {snippet}", flush=True)

@bot.message_handler(commands=["joke"], func=is_allowed)
def cmd_joke(message):
    reply = ask_ai(message.from_user.id, "Tell one short, clean football joke.")
    bot.send_message(message.chat.id, reply)

@bot.message_handler(commands=["fact"], func=is_allowed)
def cmd_fact(message):
    reply = ask_ai(message.from_user.id, "Tell me an interesting fact in football")
    bot.send_message(message.chat.id, reply)

@bot.message_handler(commands=["ucl"], func=is_allowed)
def cmd_ucl(message):
    # Ստանում ենք հրամանի արգումենտները
    args = message.text.split()
    
    # Եթե տարեթիվը կամ մրցաշրջանը նշված է (օրինակ՝ /ucl 2024)
    if len(args) > 1:
        season = args[1]
        prompt = f"You say last games in semifinals and finals of {season} UCL"
    else:
        # Եթե տարեթիվ չի նշվել, հարցնում ենք վերջին արդիական խաղերի մասին
        prompt = "You say last games in semifinals and finals of the latest UCL tournament"

    reply = ask_ai(message.from_user.id, prompt)
    bot.send_message(message.chat.id, reply)

@bot.message_handler(commands=["wc"], func=is_allowed)
def cmd_fact(message):
    # Ստանում ենք հրամանի արգումենտները
    args = message.text.split()
    
    # Եթե տարեթիվը նշված է (օրինակ՝ /wc 2014)
    if len(args) > 1:
        year = args[1]
    else:
        # Եթե ուղղակի գրել է /wc, դնում ենք վերջին հայտնի WC տարեթիվը (օրինակ՝ 2022)
        year = "2022"
        
    # Դինամիկ կերպով տեղադրում ենք տարեթիվը հարցման մեջ
    prompt = f"say who won {year} WC and say who won best player in tournament and who score most goal and say best goalkeeper and say who best younger player"

    reply = ask_ai(message.from_user.id, prompt)
    bot.send_message(message.chat.id, reply)

@bot.message_handler(commands=["roll"], func=is_allowed)
def cmd_fact(message):
    reply = ask_ai(message.from_user.id, "Tell me a football club,but different one each time")
    bot.send_message(message.chat.id, reply)

@bot.message_handler(commands=["remember"], func=is_allowed)
def cmd_remember(message):
    parts = message.text.split(maxsplit=1)
    note = parts[1] if len(parts) > 1 else ""
    
    if not note:
        bot.send_message(message.chat.id, "Please provide a note to remember! Example: /remember Buy milk")
        return

    
    store.set(f"note:{message.from_user.id}", note)
    bot.send_message(message.chat.id, "Saved!")

@bot.message_handler(commands=["recall"], func=is_allowed)
def cmd_recall(message):
    note = store.get(f"note:{message.from_user.id}")
    
    if note:
        if isinstance(note, bytes):
            note = note.decode('utf-8')
        bot.send_message(message.chat.id, f"Here is what I remembered:\n{note}")
    else:
        bot.send_message(message.chat.id, "I don't have any saved notes for you!")



@bot.message_handler(commands=["start"], func=is_allowed)
def cmd_start(message):
    bot.send_message(
        message.chat.id,
        "Hello! I'm your AI assistant. Send me a message to get started.\n\nUse /help to see available commands.",
    )


@bot.message_handler(commands=["help"], func=is_allowed)
def cmd_help(message):
    lines = [
        "/start — welcome message",
        "/help  — show this message",
        "/reset — clear conversation history",
        "/joke - say a football joke",
        "/fact - say a fooball fact",
        "/roll - say a random football club",
        "/remember - tell and the program will remember",
        "/recall - will say what he remembered",
        "/ucl - you say UCL year, and I,ll tell the last semifinals and finals in UCL",
        "/wc -You say World cup year, and I'll tell you who the win Wc,who the best player,who the most score goal,who the best gk,who the best younger player in WC"
    ]
    if HF_SPACE_ID:
        lines.append("/model — switch AI provider")
    bot.send_message(message.chat.id, "\n".join(lines))


@bot.message_handler(commands=["reset"], func=is_allowed)
def cmd_reset(message):
    clear_history(message.from_user.id)
    bot.send_message(message.chat.id, "Conversation cleared. Starting fresh!")


@bot.message_handler(commands=["about"], func=is_allowed)
def cmd_about(message):
    if HF_SPACE_ID:
        provider = get_provider(message.from_user.id)
        model_line = f"{MODEL} (main)" if provider == "main" else f"{HF_SPACE_ID} (hf)"
    else:
        model_line = MODEL
    storage_line = "SQLite" if store is not None else "stateless (no memory)"
    lines = [
        f"Model  : {model_line}",
        f"Storage: {storage_line}",
        f"Hosting: {HOSTING_LABEL}",
    ]
    if COMMIT_SHA:
        lines.append(f"Version: {COMMIT_SHA}")
    bot.send_message(message.chat.id, "\n".join(lines))


if HF_SPACE_ID:

    @bot.message_handler(commands=["model"], func=is_allowed)
    def cmd_model(message):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) == 1:
            current = get_provider(message.from_user.id)
            bot.send_message(
                message.chat.id,
                f"Current provider: {current}\n\n"
                "Options:\n"
                "/model main — Cerebras (fast, multilingual, with memory)\n"
                "/model hf — ArmGPT (Armenian only, slow, no memory)",
            )
            return
        choice = parts[1].strip().lower()
        if choice not in ("main", "hf"):
            bot.send_message(
                message.chat.id, "Invalid choice. Use: /model main or /model hf"
            )
            return
        if not set_provider(message.from_user.id, choice):
            bot.send_message(
                message.chat.id, "Could not save preference. Try again later."
            )
            return
        if choice == "hf":
            bot.send_message(
                message.chat.id,
                "Switched to hf (ArmGPT).\n\n"
                "Note: this is a tiny base completion model trained only on Armenian text. "
                "It will continue whatever you write rather than answer questions, "
                "and it does not understand English. Replies take ~30-60s and there is no memory.",
            )
        else:
            bot.send_message(message.chat.id, "Switched to Main Provider.")


@bot.message_handler(content_types=["text"], func=is_allowed)
def handle_message(message):
    if not should_respond(message):
        return
    text = (message.text or "").replace(f"@{BOT_INFO.username}", "").strip()
    if not text:
        # Edited messages, forwards, or stickers-with-empty-caption can
        # arrive with no usable text. Don't burn rate-limit / AI calls on them.
        return
    _log(message, "in", text)
    if is_rate_limited(message.from_user.id):
        limit_msg = f"You've reached the daily limit of {RATE_LIMIT} messages. Try again tomorrow."
        bot.send_message(message.chat.id, limit_msg)
        _log(message, "out", f"[rate limited] {limit_msg}")
        return
    try:
        with keep_typing(message.chat.id):
            reply = ask_ai(message.from_user.id, text)
        send_reply(message, reply)
        _log(message, "out", reply)
    except Exception as e:
        print(f"Error in handle_message: {e}")
        bot.send_message(message.chat.id, "Something went wrong. Please try again.")
        _log(message, "out", f"[error] {e}")
