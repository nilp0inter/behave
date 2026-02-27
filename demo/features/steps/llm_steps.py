from behave import given, when, then, param


@param("temperature", type=float, min=0.0, max=2.0)
@param("max_tokens", type=int, min=1, max=4096)
@given("the LLM is configured")
def step_configure_llm(context):
    print(f"  LLM configured: temperature={context.params.temperature}, "
          f"max_tokens={context.params.max_tokens}")
    context.temperature = context.params.temperature
    context.max_tokens = context.params.max_tokens


@param("model", type=str, choices=["gpt-4o", "gpt-4o-mini", "claude-sonnet", "claude-haiku"])
@param("system_prompt", type=str)
@given("the LLM model is selected")
def step_select_model(context):
    print(f"  Model: {context.params.model}")
    print(f"  System prompt: {context.params.system_prompt}")
    context.model = context.params.model


@param("block_unsafe", type=bool)
@param("log_prompts", type=bool)
@param("safety_level", type=str, choices=["strict", "moderate", "permissive"])
@given("safety filters are set")
def step_safety_filters(context):
    print(f"  Block unsafe: {context.params.block_unsafe}")
    print(f"  Log prompts: {context.params.log_prompts}")
    print(f"  Safety level: {context.params.safety_level}")


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
