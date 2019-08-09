# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.b (the "License");
# you may not use this file except in compliance with the License.
#

''' A module for helping ban group join spammers. '''

from asyncio import sleep
from requests import get

from telethon.events import ChatAction
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChannelParticipantsAdmins, Message

from userbot import BOTLOG, BOTLOG_CHATID, CMD_HELP, ANTI_SPAMBOT, ANTI_SPAMBOT_SHOUT, bot
from userbot.modules.admin import BANNED_RIGHTS, UNBAN_RIGHTS


@bot.on(ChatAction)
async def welcome_mute(welcm):
    try:
        ''' Ban a recently joined user if it
           matches the spammer checking algorithm. '''
        if not ANTI_SPAMBOT:
            return
        if welcm.user_joined or welcm.user_added:
            adder = None
            ignore = None

            if welcm.user_added:
                ignore = False
                adder = welcm._added_by

            async for admin in bot.iter_participants(welcm.chat_id, filter=ChannelParticipantsAdmins):
                if admin.id == adder:
                    ignore = True
                    break

            if ignore:
                return
            elif welcm.user_joined:
                users_list = hasattr(welcm.action_message.action, "users")
                if users_list:
                    users = welcm.action_message.action.users
                else:
                    users = [welcm.action_message.from_id]
            await sleep(5)
            spambot = False

            for user_id in users:
                async for message in bot.iter_messages(
                        welcm.chat_id,
                        from_user=user_id
                ):

                    correct_type = isinstance(message, Message)
                    if not message or not correct_type:
                        break

                    join_time = welcm.action_message.date
                    message_date = message.date

                    if message_date < join_time:
                        continue  # The message was sent before the user joined, thus ignore it

                    user = await welcm.client.get_entity(user_id)

                    # DEBUGGING. LEAVING IT HERE FOR SOME TIME ###
                    print(f"User Joined: {user.first_name} [ID: {user.id}]")
                    print(f"Chat: {welcm.chat.title}")
                    print(f"Time: {join_time}")
                    print(f"Message Sent: {message.text}\n\n[Time: {message_date}]")
                    #

                    try:
                        cas_url = f"https://combot.org/api/cas/check?user_id={user.id}"
                        r = get(cas_url, timeout = 3)
                        data = r.json()
                    except:
                        print("CAS check failed, falling back to legacy anti_spambot behaviour.")
                        pass

                    if data and data['ok']:
                        reason = f"[Banned by Combot Anti Spam](https://combot.org/cas/query?u={user.id})"
                        spambot = True
                    elif "http://" in message.text:
                        reason = "Match on `http` URLs"
                        spambot = True
                    elif "t.me" or "telegram.me" or "telegram.org" in message.text:
                        reason = "Potential Promotion Message"
                        spambot = True
                    elif message.fwd_from:
                        reason = "Forwarded Message"
                        spambot = True
                    elif "https://" in message.text:
                        reason = "Match on `https` URLs"
                        spambot = True
                    else:
                        if user.first_name in (
                                "Bitmex",
                                "Promotion",
                                "Information",
                                "Dex",
                                "Announcements",
                                "Info"
                        ):
                            if user.last_name == "Bot":
                                reason = "Known Spam Bot"
                                spambot = True

                    if spambot:
                        print(f"Potential Spam Message: {message.text}")
                        await message.delete()
                        break

                    continue  # Check the next messsage

            if spambot:
                chat = await welcm.get_chat()
                admin = chat.admin_rights
                creator = chat.creator
                if not admin and not creator:
                    if ANTI_SPAMBOT_SHOUT:
                        await welcm.reply(
                            "@admins\n"
                            "`ANTI SPAMBOT DETECTOR!\n"
                            "THIS USER MATCHES MY ALGORITHMS AS A SPAMBOT!`")
                else:
                    await welcm.reply(
                        "`Potential Spambot Detected! Kicking away! "
                        "Will log the ID for further purposes!\n"
                        f"USER:` [{user.first_name}](tg://user?id={user.id})")
                    try:
                        await welcm.client(
                            EditBannedRequest(
                                welcm.chat_id,
                                user.id,
                                BANNED_RIGHTS
                            )
                        )

                        await sleep(1)
                        await welcm.client(
                            EditBannedRequest(
                                welcm.chat_id,
                                user.id,
                                UNBAN_RIGHTS
                            )
                        )

                    except BaseException:
                        if ANTI_SPAMBOT_SHOUT:
                            await welcm.reply(
                                "@admins\n"
                                "`ANTI SPAMBOT DETECTOR!\n"
                                "THIS USER MATCHES MY ALGORITHMS AS A SPAMBOT!`")

                if BOTLOG:
                    await welcm.client.send_message(
                        BOTLOG_CHATID,
                        "#SPAMBOT-KICK\n"
                        f"USER: [{user.first_name}](tg://user?id={user.id})\n"
                        f"CHAT: {welcm.chat.title}(`{welcm.chat_id}`)\n"
                        f"REASON: {reason}\n"
                        f"MESSAGE:\n{message.text}"
                    )
    except ValueError:
        pass

CMD_HELP.update({
    'anti_spambot': "If enabled in config.env or env var, \
        this module will ban(or inform the admins about) the \
        spammer(s) if they match the userbot's algorithm"
})
