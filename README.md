# VeraBot

[![Invite](https://img.shields.io/badge/Invite%20Link-%40VeraBot-brightgreen)](https://discord.com/api/oauth2/authorize?client_id=844020223913099285&permissions=268823616&scope=bot%20applications.commands)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FnonJerry%2FVeraBot.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2FnonJerry%2FVeraBot?ref=badge_shield)
[![CodeFactor](https://www.codefactor.io/repository/github/nonjerry/verabot/badge)](https://www.codefactor.io/repository/github/nonjerry/verabot)
[![Test Status Master](https://github.com/nonJerry/VeraBot/actions/workflows/ci.yaml/badge.svg?branch=master)](https://github.com/nonJerry/VeraBot/actions/workflows/ci.yaml)
<br>

Anyone can invite this bot as long as their server doesn't share doxxing information and sticks to discord's TOS. I reserve the right to have the bot leave a server and/or close the invite again if I notice abusive beahvior.<br>
**IMPORTANT**: It is possible that the name you want to use is already taken by another server, if this is the case you will need to think of another name/variation.<br>


**VeraBot** manages the awarding of a role for membership-only content. <br>
For this it uses OCR to verify the valid access with a sent screenshot.
This bot is mainly made for VTuber Fanservers. It does not matter whether Indie or part of e.g. Hololive or Nijisanji!

## Getting started

[![Invite](https://img.shields.io/badge/Invite%20Link-%40VeraBot-brightgreen)](https://discord.com/api/oauth2/authorize?client_id=844020223913099285&permissions=268823616&scope=bot)

To invite the bot please follow the link above and grant the permissions wanted.

If you run into problems or have any suggestions, contact me on Discord at nonJerry#2416.

## Setup at the beginning

It is important that the highest role of the bot is above the membership role because it won't be able to give or remove the role otherwise! <br>

For a more detailed version including screenshots and also explaining all other settings please refer to [this document](settings.md). <br>

The initial setup commands can only be used by someone with Administrator permissions. <br>

It is required the following attributes using the given commands before the bot will work for your server:
- VTuber Name using `$setVTuber <name>`
- Membership Role using `$MemberRole <role id>`
- Log Channel using `$logChannel <channel id>`

Furthermore is it recommended to set an individual picture which will be sent with the membership-expired message.<br>
This can be done by using `$picture <Link to picture>`. Accepted formats are png, jpg and jpeg.

It is also recommended to discuss with the staff whether the bot should be able to give the role automatically to the user if it recognizes the date.
By default this is set to False but if it is wanted it can be set to true by using `$verify True`.

## Other commands

The bot has a fully functional help command. So if you want to know what commands exists just use `$help`. It will only show those commands that the user is able to use. If it is still unclear what a command does or how to use it, please contact me.

There are two commands for the management of the memberships, they all require the user to have the manage_channel permission.
1. addMember / setMember
This command requires the id and the date of the screenshot as arguments. It will then give the user the role and start managing the membership.

![addMember Command](https://user-images.githubusercontent.com/79670160/119177754-0dc2bd80-ba6d-11eb-820f-0a6bc1cadc0d.png)

2. delMember
This command only requires the id of the user. However you can also write some text which will be sent to the user in DMs.
If no text is written the user will just be notified that their membership was deleted.

![delMember Command](https://user-images.githubusercontent.com/79670160/119178160-9f322f80-ba6d-11eb-9169-66d0fed4057d.png)


Additionally there is the command `$viewMember` which will show all users who have a membership and their expiration date.
It is also possible to just view one membership by using `$viewMenber <user id>`.


## How to verify
A user can verify himself by sending the bot a DM containing the command `$verify` with a screenshot attached to it. <br>
The bot will try to map the sent screenshot by itself and sent a corresponding messaging into the set log channel of the server. <br>
However it is recommended to use `$verify <vtuber>` for fast processing. <br>

![Interaction in DMs](https://user-images.githubusercontent.com/79670160/121266335-a0ab8680-c8ba-11eb-832c-6ba0e9bb9653.png)


![Logging](https://user-images.githubusercontent.com/79670160/121266440-ccc70780-c8ba-11eb-8bfc-869b0c2c5cdd.png)


If autorole is disabled you should get a message like this into your set log channel. The reactions are to be used as followed:
<br>
:white_check_mark: -> correct date, everything fine <br>
:calendar: -> recognized date wrong / date was not recognized <br>
:no_entry_sign: -> fake / date missing on  the screenshot <br>
<br>
After selecting the bot will tell you what to do and add `VERIFIED: <verification date>` or `DENIED` to the embed and also change the reactions after the process.
<br>
![VERIFIED example](https://user-images.githubusercontent.com/79670160/121267108-f59bcc80-c8bb-11eb-8c90-81df557cda59.png)

![DENIED example](https://user-images.githubusercontent.com/79670160/121267177-149a5e80-c8bc-11eb-9ea7-f0d40b67ad49.png)


## Privacy policy

The following entails the privacy policy and agreement that you accept when adding any of VeraBot to a server, or as a member of such a server.

### Essential data collecting

This data is collected automatically. It is used for the bot to function correctly or to troubleshoot bugs that may occur in runtime.

- Server id to create a segment in the database

### Optional data collecting

This data is collected optionally when certain bot user enables or uses certain features.

- Discord Role IDs to know who is allowed to use the bot and what role to add after a successful verification
- Discord channel IDs for logging and check whether it should react to a message/reaction
- Image link coupled with the id/tag of the user who sent it and the target name
- Message sent with the verification command including all ids and attachments, id of the targeted server, used language for the text recognition and optionally a identifier string (temporarily until the process finshed - a few minutes at max)
- After a successful verification process the stored elements are:
  - user id
  - the detected date of the last membership update
  - whether the user already was informed that their membership is about to expire. Default: False
  - whether the user already was informed that their membership already expired. Default: False
  - optionally the identifier string
  - reference for what server through the DB structure

### Can I request data deletion?

Most data mentioned above (only data stored in RAM is an exception) can be permanently removed upon your request, that includes temporary stored logged data in a given timeframe. Please send nonJerry#2416 a message.

### Data storage

All stored data is kept on protected servers and it's kept on a password secured cloud storage (MongoDB Atlas). Please keep in mind that even with these protections, no data can ever be 100% secure. All efforts are taken to keep your data secure and private, but its absolute security cannot be guaranteed.

### Agreement

By adding VeraBot to your server you are consenting to the policies outlined in this document. If you, the server manager, do not agree to this document, you may remove the bot(s) from the server. If you, the server member, do not agree to this document, you may leave the server that contains the bot.


## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FnonJerry%2FVeraBot.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2FnonJerry%2FVeraBot?ref=badge_large)
