# KaedeBot
the source for the Kaede discord bot

# Adding her to your server
Use this link:

https://discordapp.com/oauth2/authorize?client_id=213099188584579072&scope=bot&permissions=0

The more permissions you give her the better. Without them, some commands (like message deletion) won't work. Look at the developer pages for discord and give her what you are comfortable with!

# Server Management
### Commands used to manage server features:
* `!addchannel <feature> [<channel_id>]`: adds the given feature to the channel specified. If no channel is specified, the current channel is used. Must be used by someone with the *Manage Server* Discord permission in the current server
* `!removechannel <feature> [<channel_id>]`: removes the given feature from the channel specified. If no channel is specified, the current channel is used. Must be used by someone with the *Manage Server* Discord permission in the current server
* `!addserver <feature>`: adds the given feature serverwide. Must be used by someone with the *Manage Server* Discord permission in the current server.
* `!removeserver <feature>`: removes the given feature serverwide. Must be used by someone with the *Manage Server* Discord permission in the current server. Does not affect the channels added manually through `!addchannel`
* `featurehelp`: displays a message similar to this one
* `featurestatus`: shows what features are currently enabled in the server
### Server features available:
* `meme`: Enables memeing features
* `imagemacro`: Bot will respond to the various *Yuru Yuri* image macro commands
* `deletion`: Bot will automatically repost messages deleted by users. Will not repost messages from itself
* `chatresponse`: Enables the Bot's cheeky chat responses
* `floodcontrol`: Bot limits users to 1 image sent per minute. Bot needs *Message Deletion* Discord Permission
* `draft`: Only able to be used by SEAL Admins
