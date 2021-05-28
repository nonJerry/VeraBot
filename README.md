# VeraBot

[![Invite](https://img.shields.io/badge/Invite%20Link-%40VeraBot-brightgreen)](https://discord.com/api/oauth2/authorize?client_id=844020223913099285&permissions=268823616&scope=bot)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FnonJerry%2FVeraBot.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2FnonJerry%2FVeraBot?ref=badge_shield)
[![CodeFactor](https://www.codefactor.io/repository/github/nonjerry/verabot/badge)](https://www.codefactor.io/repository/github/nonjerry/verabot)
<br>

*The invite is not active anymore. If you want to invite this bot please contact me on Discord nonJerry#0001.*

**VeraBot** manages the awarding of a role for membership-only content. <br>
For this it uses OCR to verify the valid access with a sent screenshot.
This bot is only available for the VTuber fanserver network.

## Getting started

[![Invite](https://img.shields.io/badge/Invite%20Link-%40VeraBot-brightgreen)](https://discord.com/api/oauth2/authorize?client_id=844020223913099285&permissions=268823616&scope=bot)

To invite the bot please follow the link above and grant the permissions wanted.

If you run into problems or have any suggestions, contact me on Discord at nonJerry#0001.

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
By default this is set to True but if it is not wanted it can be set to false by using `$verify False`.

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

![Interaction in DMs](https://user-images.githubusercontent.com/79670160/119176809-d0a9fb80-ba6b-11eb-9aec-cadfa0135937.png)

![Logging](https://user-images.githubusercontent.com/79670160/119177186-40b88180-ba6c-11eb-835b-c3d41297f42b.png)










## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FnonJerry%2FVeraBot.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2FnonJerry%2FVeraBot?ref=badge_large)
