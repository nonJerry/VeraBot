# VeraBot

[![Invite](https://img.shields.io/badge/Invite%20Link-%40VeraBot-brightgreen)](https://discord.com/api/oauth2/authorize?client_id=844020223913099285&permissions=268823616&scope=bot)
**VeraBot** manages the awarding of a role for membership-only content. <br>
For this it uses OCR to verify the valid access with a sent screenshot.

## Getting started

[![Invite](https://img.shields.io/badge/Invite%20Link-%40VeraBot-brightgreen)](https://discord.com/api/oauth2/authorize?client_id=844020223913099285&permissions=268823616&scope=bot)

To invite the bot please follow the link above and grant the permissions wanted.

If you run into problems or have any suggestions, contact me on Discord at nonJerry#0001.

## Setup at the beginning

It is required the following attributes using the given commands before the bot will work for your server:
- VTuber Name using `$setVTuber <name>`
- Membership Role using `$MemberRole <role id>`
- Log Channel using `$logChannel <channel id>`

Furthermore is it recommended to set an individual picture which will be sent with the membership-expired message.<br>
This can be done by using `$picture <Link to picture>`. Accepted formats are png, jpg and jpeg.

## How to verify
A user can verify himself by sending the bot a DM containing the command `$verify` with a screenshot attached to it. <br>
The bot will try to map the sent screenshot by itself and sent a corresponding messaging into the set log channel of the server.





