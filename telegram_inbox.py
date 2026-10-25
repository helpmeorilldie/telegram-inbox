import os
import time
import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_ID = int(os.environ["TELEGRAM_ADMIN_ID"])

API = f"https://api.telegram.org/bot{TOKEN}"


def api(method, **kwargs):
    response = requests.post(
        f"{API}/{method}",
        json=kwargs,
        timeout=40
    )
    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram API error"))

    return result["result"]


def send_text(chat_id, text, reply_to=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_to is not None:
        data["reply_parameters"] = {"message_id": reply_to}

    return api("sendMessage", **data)


def main():
    offset = None

    # Maps admin inbox message IDs to original user chat IDs.
    inbox_messages = {}

    print("Telegram inbox bot is running!")

    while True:
        try:
            params = {"timeout": 30}

            if offset is not None:
                params["offset"] = offset

            updates = requests.get(
                f"{API}/getUpdates",
                params=params,
                timeout=35
            ).json()

            if not updates.get("ok"):
                print("Could not fetch updates:", updates)
                time.sleep(2)
                continue

            for update in updates["result"]:
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]
                text = message.get("text", "")
                sender = message.get("from", {})

                # ADMIN: Reply to a message in the private admin inbox.
                if chat_id == ADMIN_ID:
                    replied = message.get("reply_to_message")

                    if replied and text:
                        original_user = inbox_messages.get(
                            replied["message_id"]
                        )

                        # Recover the mapping from the stored inbox ID.
                        if original_user is None:
                            print(
                                "Unknown inbox message. "
                                "Reply to a message received since startup."
                            )
                            continue

                        send_text(original_user, text)
                        send_text(ADMIN_ID, "✅ Reply delivered.")
                    continue

                # USER: Send incoming text to the admin inbox.
                if text == "/start":
                    send_text(
                        chat_id,
                        "Hello! Send your message here and the admin "
                        "will receive it."
                    )
                    continue

                if text:
                    name = sender.get("first_name", "Unknown")
                    username = sender.get("username", "no username")

                    admin_message = send_text(
                        ADMIN_ID,
                        f"📩 New message\n"
                        f"From: {name} (@{username})\n"
                        f"User ID: {chat_id}\n\n"
                        f"{text}"
                    )

                    inbox_messages[
                        admin_message["message_id"]
                    ] = chat_id

        except requests.RequestException as error:
            print("Network error:", error)
            time.sleep(3)
        except Exception as error:
            print("Error:", error)
            time.sleep(2)


if __name__ == "__main__":
    main()
