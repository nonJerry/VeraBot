Feature: Daily Check
  Rule: Prior Notice
    Scenario Outline: Prior Notice is sent
      Given a prior notice period of <time> days
      And I have a active verification until <time> - 1 days into the future
      When a the (daily) check is run
      Then I get a DM with an embed from the bot stating
      """Your membership to <server> will expire within the next <time * 24> hours.
         If you do not want to lose this membership please don't forget to renew it!
      """

      Examples:
        | time |
        | 1    |
        | 2    |
        | 3    |
        | 4    |

    Scenario Outline: Prior Notice is not sent
      Given a prior notice period of <time> days
      And I have a active verification until <time> days into the future
      When a the (daily) check is run
      Then Then I get no message from the bot

      Examples:
        | time |
        | 1    |
        | 2    |
        | 3    |
        | 4    |

    Scenario: No active prior notice
      Given a prior notice period of 0 days
      And I have a active verification until today
      When a the (daily) check is run
      Then I get no message from the bot

  Rule: Grace Period retains role

    Scenario: Message on verification end
      Given a verification until yesterday
      And a grace period of 1 day
      And a already sent prior notice
      When a the (daily) check is run
      Then I get a DM from the bot stating I have X days left

    Scenario Outline Outline: Role is not lost
      Given a grace period of <time> days
      And I have a active verification until <time> days ago
      When a the (daily) check is run
      Then Then I get no message from the bot

      Examples:
        | time |
        | 0    |
        | 1    |
        | 2    |

    Scenario Outline: Role is lost
      Given a grace period of <time> days
      And I have a active verification until <time> + 1 days ago
      When a the (daily) check is run
      Then Then I get a DM from the bot stating that I have lost access to the channel
      And my role was removed

      Examples:
        | time |
        | 0    |
        | 1    |
        | 2    |
