Feature: LLM response generation

  Scenario: Generate a greeting
    Given the LLM is configured
    When the user says "hello"
    Then a response is generated within the token limit
