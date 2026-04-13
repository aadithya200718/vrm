# How Agents Call Tools - Complete Mechanism

## Overview

Agents don't directly call tools. Instead, the LLM (Language Model) decides which tools to call based on:
1. The task it's given
2. The tools available to it
3. The current context/state
4. Previous tool results

This document explains the complete mechanism of how this works.

---

## The Tool Calling Flow

```
User Request
    ↓
Agent receives task
    ↓
LLM sees:
  - Task description
  - Available tools (names, descriptions, parameters)
  - Current context
    ↓
LLM reasons: "What do I need to do?"
    ↓
LLM decides: "I need to call tool X with parameters Y"
    ↓
LLM generates function call in specific format
    ↓
Framework intercepts the function call
    ↓
Framework executes the actual Python function
    ↓
Framework returns result to LLM
    ↓
LLM sees the result
    ↓
LLM reasons: "What should I do next?"
    ↓
Loop continues until task complete
```

---

## Step-by-Step: How It Actually Works

### Step 1: Tool Definition

First, you define tools as Python functions with special decorators:

```python
from langchain.tools import tool

@tool
def search_security_policies(query: str) -> list:
    """
    Search security policy database using semantic search.
    
    Args:
        query: Natural language query about security requirements
        
    Returns:
        list of relevant policy excerpts
    """
    # Actual implementation
    results = vector_store.search(query)
    return results
```

**What the LLM sees:**
```
Tool Name: search_security_policies
Description: Search security policy database using semantic search.
Parameters:
  - query (string, required): Natural language query about security requirements
Returns: list of relevant policy excerpts
```

### Step 2: Agent Creation

You create an agent and give it access to tools:

```python
from langchain.agents import create_openai_functions_agent
from langchain_openai import ChatOpenAI

# Define tools list
tools = [
    search_security_policies,
    validate_soc2_certificate,
    scan_domain_security,
    calculate_security_score
]

# Create LLM
llm = ChatOpenAI(model="gpt-4", temperature=0)

# Create agent with tools
agent = create_openai_functions_agent(
    llm=llm,
    tools=tools,
    prompt=agent_prompt
)
```

### Step 3: Agent Receives Task

```python
# User gives task to agent
result = agent.invoke({
    "input": "Review Acme Corp's security posture",
    "vendor_name": "Acme Corp",
    "documents": ["soc2_report.pdf"]
})
```

### Step 4: LLM Sees the Prompt

The LLM receives a prompt that looks like this:

```
System: You are a security review specialist.

Available Tools:
1. search_security_policies(query: str) -> list
   Search security policy database using semantic search.
   
2. validate_soc2_certificate(cert_data: dict) -> dict
   Verify SOC2 Type 2 authenticity and validity.
   
3. scan_domain_security(domain: str) -> dict
   External security scan (SSL, headers, vulnerabilities).
   
4. calculate_security_score(findings: dict) -> dict
   Weighted risk score calculation.

Task: Review Acme Corp's security posture
Context:
  - Vendor: Acme Corp
  - Documents: soc2_report.pdf

Think step by step and use your tools to complete the task.
```

### Step 5: LLM Reasons and Decides

The LLM thinks (internally):

```
"I need to review Acme Corp's security. Let me think:
1. First, I should check what security requirements apply
2. I have a tool called 'search_security_policies' that can help
3. I'll call it with a query about security requirements"
```

### Step 6: LLM Generates Function Call

The LLM outputs a special format indicating it wants to call a tool:

**OpenAI Function Calling Format:**
```json
{
  "role": "assistant",
  "content": null,
  "function_call": {
    "name": "search_security_policies",
    "arguments": "{\"query\": \"security requirements for SaaS vendors\"}"
  }
}
```

**Anthropic Tool Use Format:**
```json
{
  "role": "assistant",
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lq9",
      "name": "search_security_policies",
      "input": {
        "query": "security requirements for SaaS vendors"
      }
    }
  ]
}
```

### Step 7: Framework Intercepts and Executes

LangChain/LangGraph sees the function call and:

1. Parses the function name: `search_security_policies`
2. Parses the arguments: `{"query": "security requirements for SaaS vendors"}`
3. Finds the actual Python function
4. Calls it: `search_security_policies("security requirements for SaaS vendors")`
5. Gets the result

```python
# Framework does this automatically:
tool_name = "search_security_policies"
tool_args = {"query": "security requirements for SaaS vendors"}

# Find the tool
tool_function = tool_registry[tool_name]

# Execute it
result = tool_function(**tool_args)

# Result:
# [
#   {"policy": "SOC2 Type 2 required for SaaS vendors", "score": 0.95},
#   {"policy": "Penetration testing within 12 months", "score": 0.87}
# ]
```

### Step 8: Result Returned to LLM

The framework sends the result back to the LLM in a special format:

**OpenAI Format:**
```json
{
  "role": "function",
  "name": "search_security_policies",
  "content": "[{\"policy\": \"SOC2 Type 2 required for SaaS vendors\", \"score\": 0.95}, {\"policy\": \"Penetration testing within 12 months\", \"score\": 0.87}]"
}
```

**Anthropic Format:**
```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
      "content": "[{\"policy\": \"SOC2 Type 2 required for SaaS vendors\", \"score\": 0.95}, {\"policy\": \"Penetration testing within 12 months\", \"score\": 0.87}]"
    }
  ]
}
```

### Step 9: LLM Sees Result and Reasons Again

The LLM now sees:

```
Tool Result from search_security_policies:
[
  {"policy": "SOC2 Type 2 required for SaaS vendors", "score": 0.95},
  {"policy": "Penetration testing within 12 months", "score": 0.87}
]

The LLM thinks:
"Good! I found that SOC2 Type 2 is required. 
They submitted a soc2_report.pdf, so let me validate it.
I'll call the validate_soc2_certificate tool."
```

### Step 10: LLM Calls Next Tool

```json
{
  "role": "assistant",
  "function_call": {
    "name": "validate_soc2_certificate",
    "arguments": "{\"cert_data\": {\"file\": \"soc2_report.pdf\"}}"
  }
}
```

### Step 11: Loop Continues

This process repeats:
- LLM calls tool
- Framework executes tool
- Result returned to LLM
- LLM reasons about result
- LLM decides next action
- Either call another tool or finish

---

## Complete Example: Security Review

### Initial State

```python
# Agent is created with tools
security_agent = create_agent(
    tools=[
        search_security_policies,
        validate_soc2_certificate,
        scan_domain_security,
        calculate_security_score,
        generate_security_report
    ]
)

# Task is given
result = security_agent.invoke({
    "input": "Review Acme Corp security",
    "vendor": "Acme Corp",
    "domain": "acme.com",
    "documents": ["soc2_report.pdf"]
})
```

### Execution Trace

**Turn 1: LLM Reasoning**
```
LLM thinks: "I need to review security. Let me check requirements first."
```

**Turn 1: LLM Action**
```json
{
  "function_call": {
    "name": "search_security_policies",
    "arguments": "{\"query\": \"SaaS vendor security requirements\"}"
  }
}
```

**Turn 1: Tool Execution**
```python
# Framework executes:
result = search_security_policies("SaaS vendor security requirements")
# Returns: [{"policy": "SOC2 Type 2 required"}, {"policy": "Pen test required"}]
```

**Turn 1: Result to LLM**
```
Tool Result: [{"policy": "SOC2 Type 2 required"}, {"policy": "Pen test required"}]
```

---

**Turn 2: LLM Reasoning**
```
LLM thinks: "SOC2 is required. They have soc2_report.pdf. Let me validate it."
```

**Turn 2: LLM Action**
```json
{
  "function_call": {
    "name": "validate_soc2_certificate",
    "arguments": "{\"cert_data\": {\"file\": \"soc2_report.pdf\"}}"
  }
}
```

**Turn 2: Tool Execution**
```python
# Framework executes:
result = validate_soc2_certificate({"file": "soc2_report.pdf"})
# Returns: {"valid": true, "type": "Type 2", "expires": "2025-12-31"}
```

**Turn 2: Result to LLM**
```
Tool Result: {"valid": true, "type": "Type 2", "expires": "2025-12-31"}
```

---

**Turn 3: LLM Reasoning**
```
LLM thinks: "SOC2 is valid. Now let me scan their domain for security issues."
```

**Turn 3: LLM Action**
```json
{
  "function_call": {
    "name": "scan_domain_security",
    "arguments": "{\"domain\": \"acme.com\"}"
  }
}
```

**Turn 3: Tool Execution**
```python
# Framework executes:
result = scan_domain_security("acme.com")
# Returns: {"ssl_score": "A+", "security_headers": "Good", "score": 95}
```

**Turn 3: Result to LLM**
```
Tool Result: {"ssl_score": "A+", "security_headers": "Good", "score": 95}
```

---

**Turn 4: LLM Reasoning**
```
LLM thinks: "Good security posture. Let me calculate the overall score."
```

**Turn 4: LLM Action**
```json
{
  "function_call": {
    "name": "calculate_security_score",
    "arguments": "{\"findings\": {\"soc2_valid\": true, \"domain_score\": 95}}"
  }
}
```

**Turn 4: Tool Execution**
```python
# Framework executes:
result = calculate_security_score({"soc2_valid": true, "domain_score": 95})
# Returns: {"score": 87, "grade": "B+"}
```

**Turn 4: Result to LLM**
```
Tool Result: {"score": 87, "grade": "B+"}
```

---

**Turn 5: LLM Reasoning**
```
LLM thinks: "I have all the information. Let me generate the final report."
```

**Turn 5: LLM Action**
```json
{
  "function_call": {
    "name": "generate_security_report",
    "arguments": "{\"findings\": {\"soc2\": \"valid\", \"domain\": 95, \"score\": 87}}"
  }
}
```

**Turn 5: Tool Execution**
```python
# Framework executes:
result = generate_security_report({"soc2": "valid", "domain": 95, "score": 87})
# Returns: {"report": {...}, "summary": "Strong security posture"}
```

**Turn 5: Result to LLM**
```
Tool Result: {"report": {...}, "summary": "Strong security posture"}
```

---

**Turn 6: LLM Reasoning**
```
LLM thinks: "Task complete. I have the report."
```

**Turn 6: LLM Final Response**
```
{
  "role": "assistant",
  "content": "Security review complete. Acme Corp has a strong security posture with a score of 87/100 (B+). SOC2 Type 2 certificate is valid until 2025-12-31, and domain security is excellent with A+ SSL rating."
}
```

---

## How LangChain/LangGraph Handles This

### LangChain Agent Executor

```python
from langchain.agents import AgentExecutor

# Create agent executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,  # Shows the reasoning
    max_iterations=10,  # Prevent infinite loops
    handle_parsing_errors=True
)

# Execute
result = agent_executor.invoke({"input": "Review security"})
```

**What AgentExecutor does:**
1. Sends initial prompt to LLM
2. Receives LLM response
3. Checks if it's a function call
4. If yes:
   - Executes the function
   - Sends result back to LLM
   - Repeats
5. If no (final answer):
   - Returns result to user

### LangGraph State Machine

```python
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent

# Create agent with tools
security_agent = create_react_agent(
    model=llm,
    tools=tools,
    state_modifier="You are a security reviewer"
)

# LangGraph handles the loop automatically
result = security_agent.invoke({
    "messages": [("user", "Review Acme Corp security")]
})
```

**What LangGraph does:**
1. Maintains state across tool calls
2. Handles the ReAct loop (Reason → Act → Observe)
3. Manages parallel tool execution
4. Handles errors and retries
5. Provides checkpointing

---

## Tool Calling Formats by Provider

### OpenAI Function Calling

**Request to OpenAI:**
```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "You are a security reviewer"},
    {"role": "user", "content": "Review Acme Corp security"}
  ],
  "functions": [
    {
      "name": "search_security_policies",
      "description": "Search security policy database",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "Search query"
          }
        },
        "required": ["query"]
      }
    }
  ]
}
```

**Response from OpenAI:**
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "function_call": {
          "name": "search_security_policies",
          "arguments": "{\"query\": \"SaaS security requirements\"}"
        }
      }
    }
  ]
}
```

### Anthropic Tool Use

**Request to Anthropic:**
```json
{
  "model": "claude-3-sonnet-20240229",
  "messages": [
    {"role": "user", "content": "Review Acme Corp security"}
  ],
  "tools": [
    {
      "name": "search_security_policies",
      "description": "Search security policy database",
      "input_schema": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "Search query"
          }
        },
        "required": ["query"]
      }
    }
  ]
}
```

**Response from Anthropic:**
```json
{
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_123",
      "name": "search_security_policies",
      "input": {
        "query": "SaaS security requirements"
      }
    }
  ]
}
```

### Ollama (Local LLM)

Ollama supports function calling with compatible models:

**Request:**
```json
{
  "model": "llama3",
  "messages": [
    {"role": "user", "content": "Review security"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search_security_policies",
        "description": "Search security policies",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {"type": "string"}
          }
        }
      }
    }
  ]
}
```

---

## Key Points

### 1. LLM Decides, Framework Executes

```
❌ Wrong: Agent directly calls Python function
✅ Right: LLM decides to call function, framework executes it
```

### 2. Tools are Described to LLM

The LLM never sees the actual Python code. It only sees:
- Tool name
- Tool description
- Parameter names and types
- Return type description

### 3. Framework is the Bridge

```
LLM World                Framework                Python World
(Text/JSON)              (LangChain)              (Actual Code)
    │                        │                         │
    │  "Call tool X"         │                         │
    ├───────────────────────>│                         │
    │                        │  Execute function X     │
    │                        ├────────────────────────>│
    │                        │                         │
    │                        │  Return result          │
    │                        │<────────────────────────┤
    │  "Here's result"       │                         │
    │<───────────────────────┤                         │
```

### 4. Autonomous Decision Making

The LLM autonomously decides:
- Which tool to call
- What parameters to pass
- When to call the next tool
- When the task is complete

No hardcoded logic tells it what to do.

### 5. ReAct Loop

```
Reason: "I need to check security requirements"
  ↓
Act: Call search_security_policies("SaaS requirements")
  ↓
Observe: Received policy list
  ↓
Reason: "SOC2 is required, let me validate their certificate"
  ↓
Act: Call validate_soc2_certificate(cert_data)
  ↓
Observe: Certificate is valid
  ↓
Reason: "Good, now let me scan their domain"
  ↓
... continues until complete
```

---

## Error Handling

### Tool Execution Errors

```python
@tool
def validate_soc2_certificate(cert_data: dict) -> dict:
    """Validate SOC2 certificate"""
    try:
        # Actual validation
        result = validate_cert(cert_data)
        return result
    except Exception as e:
        # Return error to LLM
        return {
            "error": str(e),
            "valid": False,
            "message": "Certificate validation failed"
        }
```

**LLM sees the error and adapts:**
```
Tool Result: {"error": "File not found", "valid": false}

LLM thinks: "The certificate file wasn't found. I should flag this as missing evidence."
```

### Invalid Parameters

If LLM provides invalid parameters, the framework catches it:

```python
# LLM tries to call with wrong type
function_call = {
    "name": "calculate_security_score",
    "arguments": {"findings": "not a dict"}  # Wrong type!
}

# Framework validates and returns error
error = "Parameter 'findings' must be dict, got str"

# Error sent back to LLM
# LLM tries again with correct parameters
```

---

## Performance Optimization

### Tool Result Caching

```python
from functools import lru_cache

@tool
@lru_cache(maxsize=100)
def search_security_policies(query: str) -> list:
    """Search with caching"""
    return vector_store.search(query)
```

### Parallel Tool Execution

```python
# LLM can request multiple tools at once
function_calls = [
    {"name": "validate_soc2_certificate", "args": {...}},
    {"name": "scan_domain_security", "args": {...}},
    {"name": "check_breach_history", "args": {...}}
]

# Framework executes in parallel
results = await asyncio.gather(
    validate_soc2_certificate(...),
    scan_domain_security(...),
    check_breach_history(...)
)

# All results returned to LLM together
```

---

## Debugging Tool Calls

### Enable Verbose Mode

```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True  # Shows all tool calls
)
```

**Output:**
```
> Entering new AgentExecutor chain...

Thought: I need to check security requirements first
Action: search_security_policies
Action Input: {"query": "SaaS vendor security requirements"}
Observation: [{"policy": "SOC2 Type 2 required"}]

Thought: SOC2 is required, let me validate their certificate
Action: validate_soc2_certificate
Action Input: {"cert_data": {"file": "soc2_report.pdf"}}
Observation: {"valid": true, "expires": "2025-12-31"}

Thought: Certificate is valid, let me scan their domain
Action: scan_domain_security
Action Input: {"domain": "acme.com"}
Observation: {"score": 95}

Thought: I have enough information to generate the report
Final Answer: Security review complete with score 87/100
```

### LangSmith Tracing

LangSmith provides visual tracing of all tool calls:
- See exact prompts sent to LLM
- See tool calls and parameters
- See tool results
- See LLM reasoning
- Measure latency

---

## Summary

**How tools are called:**

1. **You define tools** as Python functions with `@tool` decorator
2. **You give tools to agent** when creating it
3. **LLM sees tool descriptions** (not the code)
4. **LLM decides to call a tool** based on the task
5. **LLM outputs function call** in special JSON format
6. **Framework intercepts** the function call
7. **Framework executes** the actual Python function
8. **Framework returns result** to LLM
9. **LLM sees result** and decides next action
10. **Loop continues** until task complete

**Key insight:** The LLM is having a conversation with the tools through the framework. It never directly executes code - it just decides what should be executed, and the framework does the actual execution.

This is what makes it autonomous - the LLM is making all the decisions about which tools to call and when, based on reasoning about the task and the results it receives.
