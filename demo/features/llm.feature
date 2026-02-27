Feature: LLM response generation

  Scenario: Generate a greeting
    Given the LLM is configured
    When the user says "hello"
    Then a response is generated within the token limit

  Scenario: Generate with full options
    Given the LLM model is selected
    And the LLM is configured
    And safety filters are set
    When the user says "tell me a story"
    Then a response is generated within the token limit
