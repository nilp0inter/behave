from behave import given, when, then, param


@param("temperature", type=float, min=0.0, max=2.0)
@param("max_tokens", type=int, min=1, max=4096)
@given("the LLM is configured")
def step_configure_llm(context):
    print(f"  LLM configured: temperature={context.params.temperature}, "
          f"max_tokens={context.params.max_tokens}")
    context.temperature = context.params.temperature
    context.max_tokens = context.params.max_tokens


@when('the user says "{message}"')
def step_user_says(context, message):
    print(f"  User says: {message}")
    context.user_message = message


@param("response_timeout", type=float, min=0.1, max=60.0)
@then("a response is generated within the token limit")
def step_response_generated(context):
    print(f"  Response timeout: {context.params.response_timeout}s")
    print(f"  Max tokens allowed: {context.max_tokens}")
    # In a real test, this would call an LLM and check the response.
    assert context.temperature >= 0.0
    assert context.max_tokens >= 1
