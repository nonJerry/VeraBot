# Settings explained

This document will explain settings that you can set for VeraBot including screenshots for easier understanding. <br>
Also it is always possible to use `$help` for infos about the commands without looking here.

## Basic Setup

When the bot joins it will need certain settings to be set before you can start to use it. Mandatory are VTuber, Log Channel and Member Role. <br>
1. Setting the VTuber <br>
    **Important:** The used name needs to be found in the Membership screenshot. So for example `Yukihana Lamy` is not valid because her membership screenshot only shows `Lamy`!<br>
    <br>
    To set the VTuber name you need to use `$setVtuber <vtuber>`. If you want to use the full name and it contains spaces you will need to set it in quotes, e.g. `$setVtuber "Kureiji Ollie"`. <br> 
    It is also not recommended to use the full channel name because the recognition used looks for a full match; during this it often does not recognize points and hyphens, so please try not to use them for your own convenience. <br>
    <br>
    ![set VTuber](https://user-images.githubusercontent.com/79670160/119546498-45df3e80-bd94-11eb-875f-9fef279d161e.png) <br>


2. Setting the Log Channel <br>
    To set the Log Channel you need to use `$setLogChannel <channel id>`. The bot will verify whether the id used is a legit channel. However it will not check whether it has all needed rights for this channel! The bot will not work if it does not, so please check whether you have given it the same rights on your log channel as the VeraBot role has. <br>
    <br>
    ![set Log Channel](https://user-images.githubusercontent.com/79670160/119546565-54c5f100-bd94-11eb-8333-8c9fc35f251f.png) <br>

3. Setting the Member Role <br>
    To set the Member Role you need to use `setMemberRole <role id>`. The bot will verify whether the id is a legit role. Furthermore the highest role of the bot needs to be above the role it is supposed to give. Otherwise it will not work because of permission issues. <br>
    <br>
    ![set Member Role](https://user-images.githubusercontent.com/79670160/119546608-63140d00-bd94-11eb-945c-2bd974891675.png) <br>

#### The basic setup would look like this: <br>
![Full Basic Setup](https://user-images.githubusercontent.com/79670160/119546642-6e673880-bd94-11eb-9bb2-59f9bd3fce4b.png)


## Advanced Setup

Those are settings that are optional but useful to customize the experience for your server. <br>

### Viewing your current settings ($settings) <br>
  This is a useful command which will show you all your current settings in an embed. The added picture is the one that will sent with the expiry message to the user. <br>
  <br>
  ![View Settings](https://user-images.githubusercontent.com/79670160/119546693-7d4deb00-bd94-11eb-876e-59419069b0cc.png) <br>

### Expiry picture ($picture \<link>) <br>
  You may want to set the picture which will be sent to the user each time they are reminded that their membership is about to end/has ended. <br>
  For this you use `$picture <link>`. The link should not expire after a certain time but be permanent as the bot does not save the picture but the link itself. Additionally it the bot will only accept links that end with .jpg, .jpeg and .png. <br>
  <br>
  ![Set Picture](https://user-images.githubusercontent.com/79670160/119549101-2d245800-bd97-11eb-97d0-38fc4ab90a82.png) <br>

### Auto Role ($auto [True|False]) <br>
  This decides whether the bot is allowed to give the member role to the user once it recognizes a date. This is set to false by default.<br>
  You can be set it by using `$auto [True|False]`. It only accepts the values True and False. <br>
  <br> 
  ![Set Auto Role](https://user-images.githubusercontent.com/79670160/119546747-8d65ca80-bd94-11eb-9b87-d955f024455a.png) <br>
    
### Require Additional Proof ($setRequireProof [True|False]) <br>
  This decides whether the bot will ask the user to send an additional screenshot as further proof. The bot will not check this proof, it will need to be done by the staff. <br>
  It is recommended but not required to use this with auto role off. <br>
  To set this you need to use `$setRequireProof [True|False]` It only accepts the values True and False. <br>
  <br> 
  ![Set Require Proof](https://user-images.githubusercontent.com/79670160/119546814-a1113100-bd94-11eb-8bf7-fe69edff5c87.png) <br>

### Tolerance Duration ($setTolerance \<days>) <br>
  This duration expresses how many days the user will have access to the membership channel after their membership expired. It is set to 1 day by default. <br>
  It can be set using `$setTolerance <days>`. Only positive values are accepted. <br>
  <br> 
  ![Set Tolerance Duration](https://user-images.githubusercontent.com/79670160/119546929-c0a85980-bd94-11eb-997a-996d4b0b3640.png) <br>

### Prior Notice Duration ($setPriorNotice \<days>) <br>
  This duration expresses how many days before the user's membership will end the bot will contact them warning that their membership (not access to channel) is about to end. It is set to 1 by default. <br>
  If set to 0 there will be not notice at all. It can be set using `$setPriorNotice <days>`. Only positive values are accepted. <br>
  <br> 
  ![image](https://user-images.githubusercontent.com/79670160/119547008-db7ace00-bd94-11eb-8fe9-77dee45cd5c2.png) <br>

### Prefixes
  1. Set <br>
      You can add as many prefixes as you like. The bot will listen to them additionally to the already set `$`. <br>
      To set a prefix use `$prefix <new prefix>`. Only prefixes without space should be used. <br>
      <br> 
      ![Set Prefix](https://user-images.githubusercontent.com/79670160/119547115-fc432380-bd94-11eb-8847-894ac0dc0c1c.png) <br>
  
  2. Remove <br>
      If you don't want a certain prefix anymore you can remove it using `$removePrefix <prefix>`. <br>
      If all prefixes are removed the bot will listen start listening to `$` even if you removed it before. <br>
      <br> 
      ![Remove Prefix](https://user-images.githubusercontent.com/79670160/119548403-7a53fa00-bd96-11eb-8bb5-737d9ca3dedf.png) <br>

  3. View <br>
      To view all prefixes you can use `$showPrefix`. It will simply list all that are listened to at this server. <br>
      <br> 
      ![View Prefix](https://user-images.githubusercontent.com/79670160/119548651-b5eec400-bd96-11eb-85ec-aa19da080dab.png)


