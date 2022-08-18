Feature: Verification

  Rule: Relay Verification to log channel
    Scenario: No log channel set
      Given there is no log channel set
      When a valid verification is submitted
      Then the bot will reply
      """Your proof has been added to the queue and will be processed later.
         You will get a message when your role is applied."""
      And the bot will reply "Please contact the staff of your server, they forgot to set some settings"

    Scenario: No date visible
      Given the bot is set up for the server
      When a verification without visible date is submitted
      Then there will be a message with embed showing the sent image in the log channel
      And the verification message in the log channel shows the user's name
      And the verification message in the log channel shows that there was no date detected

    Scenario: Date visible
      Given the bot is set up for the server
      When a verification without visible date is submitted
      Then there will be a message with embed showing the sent image in the log channel
      And the verification message shows the user's name
      And the verification message shows the date of the sent image

  Rule: Approved Proof grants role
    Scenario Outline: Without recognized date
      Given there is a verification message sent before <time>
      When I approve the verification
      Then the bot replies "Please use 'no/wrong date recognized' instead"
      And no member role is added to the user

      Examples:
        | time          |
        | 1 minute      |
        | 1 day         |
        | a bot restart |

    Scenario Outline: With recognized date
      Given there is a verification message sent before <time>
      When I approve the verification
      Then the verification message shows who approved it
      And the verification message shows that it was approved
      And the member role is added to the user

      Examples:
        | time          |
        | 1 minute      |
        | 1 day         |
        | a bot restart |

  Rule: Approval with changed date grants role
    Scenario Outline: Change date
      Given there is a verification message sent before <time>
      When I approve the verification with a different date
      Then the bot replies
        """Please write the correct date from the screenshot in the format dd/mm/yyyy.
           Type CANCEL to stop the process."""
      When I write the date of today
      Then the verification message shows who approved it
      And the verification message shows that it was approved
      And the verification message show today as verification date
      And the member role is added to the user

      Examples:
        | time          |
        | 1 minute      |
        | 1 day         |
        | a bot restart |

  Rule: Denied proof does not grant role
    Scenario Outline: Denied Proof
      Given there is a verification message sent before <time>
      When I deny the verification
      Then the bot replies "Please write a message that will be sent to the User.Type CANCEL to stop the process."
      When I write "missing date"
      Then the bot replies "Message was sent to <user>"
      And the bot sends a DM to the user stating the server and containing the message "missing date"
      And no member role is added to the user

      Examples:
        | time          |
        | 1 minute      |
        | 1 day         |
        | a bot restart |

  Rule: Newer date takes precedence over older date for manual addition
    Scenario Outline: Older date does not overwrite
      Given a person has the verification date today
      And submitted a proof with the date <date>
      When I approve the verification
      Then the verification date is today

      Examples:
        | date       |
        | yesterday  |
        | a week ago |
        | today      |

    Scenario: Newer date takes precedence
      Given a person has the verification date yesterday
      And submitted a proof with the date today
      When I approve the verification
      Then the verification date is today

  Rule: Auto automatically accepts/denies proof
    Scenario: Proof is accepted
      Given the Auto Role setting is enabled
      When I submit a valid proof with the date today
      Then the member role is added to me
      And a verification message with embed is sent to the log channel

    Scenario: Proof is denied
      Given the Auto Role setting is enabled
      When I submit a proof without date
      Then no member role is added to me
      And a verification message with embed is sent to the log channel