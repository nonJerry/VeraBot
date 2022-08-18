Feature: Server Setup

  Rule: Used IDs need to exist
    Scenario: Member role does not exist
      When I set the member role to a non-existent role id
      Then the bot replies "ID does not refer to a legit role"
      And the set member role did not change

    Scenario: Member role does exist
      When I set the member role to an existing role id
      Then the bot replies "Member role id set to <role id>"
      And the set member role is <role id>

    Scenario: Log Channel does not exist
      When I set the log channel to a non-existent channel id
      Then the bot replies "ID does not refer to a legit channel"
      And the set log channel did not change

    Scenario: Log Channel does exist
      When I set the log channel to an existing channel id
      Then the bot replies "Log Channel id set to <channel id>"
      And the set log channel is <log channel>

    Scenario: Proof Channel does not exist
      When I set the proof channel to a non-existent channel id
      Then the bot replies "Please use a valid channel!"
      And the set proof channel did not change

    Scenario: Proof Channel does exist
      When I set the proof channel to an existing channel id
      Then the bot replies "Proof Channel id set to <channel id>"
      And the set proof channel is <log channel>

  Rule: Other settings restrictions are adhered to
    Scenario Outline: Only true and false accepted for certain settings
      When try to set <setting> to <value>
      Then the bot replies <reply text>
      And the <setting> is <new value>

      Examples:
        | setting                  | value | reply text                                    | new value   |
        | Auto Role Flag           | True  | Flag for automatic role handling set to True  | True        |
        | Auto Role Flag           | False | Flag for automatic role handling set to False | False       |
        | Auto Role Flag           | dasds |                                               | <unchanged> |
        | Require Additional Proof | true  | Flag for additional Proof set to True         | True        |
        | Require Additional Proof | false | Flag for additional Proof set to False        | False       |
        | Require Additional Proof | 12367 |                                               | <unchanged> |
        | Logging enabled          | True  | Flag for logging set to True                  | True        |
        | Logging enabled          | False | Flag for logging set to False                 | False       |
        | Logging enabled          | 12367 |                                               | <unchanged> |

  Rule: Multi Server can be activated/disabled
    Scenario: Enabling Multi Server from Single Server
      Given multi server is disabled
      When I activate multi server
      Then the bot replies "Management of several talents was activated for this  server!"
      And the flag for multi server is set to true

    Scenario: Enabling Multi Server from Multi Server
      Given multi server is activated
      When I activate multi server
      Then the bot replies "Your server already has enabled the usage of multiple talents!"
      And the flag for multi server is set to true

    Scenario: Disabling Multi Server from Multi Server
      Given multi server is activated
      When I disable multi server
      # TODO: Change in code
      Then the bot replies "Management of several talents was disabled for this server!"
      And the flag for multi server is set to false

    Scenario: Disabling Multi Server from Single Server
      Given multi server is disabled
      When I disable multi server
      Then the bot replies "Your server has not enabled the usage of multiple talents!"

  Rule: Threading can be activated/disabled
    Scenario: Enabling threads without set proof channel
      Given threads are disabled
      And no proof channel is set
      When I activate threads
      Then the bot replies "Please set a proof channel first!"

    Scenario: Enabling threads with set proof channel
      Given threads are disabled
      And proof channel <channel id> is set
      When I activate threads
      Then the bot replies "Flag for using threads set to True"
      And Threads enabled is set to true

    Scenario: Disabling threads
      Given threads are enabled
      And proof channel <channel id> is set
      When I disable threads
      Then the bot replies "Flag for using threads set to False"
      And Threads enabled is set to false

  Rule: Durations can be set freely within limits
    Scenario: Tolerance Duration cannot be higher than 2 days
      Given the tolerance duration is set to 1 day
      When I set the tolerance duration to 3 days
      Then the bot replies "This value cannot be more than 2 days."
      And the tolerance duration is 1 day

    Scenario: Tolerance Duration cannot be less than 0 days
      Given the tolerance duration is set to 1 day
      When I set the tolerance duration to -1 days
      Then the bot replies "This value needs to be at least 0 days."
      And the tolerance duration is 1 day

    Scenario: Tolerance Duration can be exactly 0 days
      Given the tolerance duration is set to 1 day
      When I set the tolerance duration to 0 days
      Then the bot replies "Time that users will still have access to the channel after their membership expired set to 0 days."
      And the tolerance duration is 0 day

    Scenario: Prior Notice Duration cannot be less than 0 days
      Given the prior notice duration is set to 1 day
      When I set the prior notice duration to -1 days
      Then the bot replies "This value needs to be at least 0 days."
      And the prior notice duration is 1 day

      # TODO: Change in code
    Scenario: Prior Notice Duration cannot be more than 6 days
      Given the prior notice duration is set to 1 day
      When I set the prior notice duration to 7 days
      Then the bot replies "This value cannot be more than 6 days."
      And the prior notice duration is 1 day

    Scenario: Prior Notice Duration can be exactly 0 days
      Given the prior notice duration is set to 1 day
      When I set the prior notice duration to 0 days
      Then the bot replies "Users will be notified 0 days before their membership ends."
      And the prior notice duration is 0 day
