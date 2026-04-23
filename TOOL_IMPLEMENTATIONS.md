# Tool Implementation Guide

## How Tools Work in Agent Systems

Tools are **Python functions** that agents can call. The LLM sees:
1. Tool name
2. Tool description
3. Tool parameters
4. Tool return type

The LLM decides when to call them based on the task.

---

## Tool Implementation Patterns

### Pattern 1: Simple API Call Tool

```python
from langchain.tools import tool
import requests

@tool
def get_credit_rating(company_name: str) -> dict:
    """
    Get credit rating for a company from Dun & Bradstreet API.
    
    Args:
        company_name: Full legal name of the company
        
    Returns:
        dict with rating, score, and risk level
    """
    # Call external API
    response = requests.post(
        "https://api.dnb.com/v1/credit-rating",
        headers={"Authorization": f"Bearer {DNB_API_KEY}"},
        json={"company_name": company_name}
    )
    
    data = response.json()
    
    return {
        "company": company_name,
        "rating": data.get("rating"),  # e.g., "3A1"
        "score": data.get("score"),    # e.g., 85
        "risk_level": data.get("risk"), # e.g., "Low"
        "last_updated": data.get("date")
    }
```

**How the agent uses it:**
```
Agent thinks: "I need to check financial stability"
Agent calls: get_credit_rating("Acme Corp")
Agent receives: {"rating": "3A1", "score": 85, "risk_level": "Low"}
Agent thinks: "Good rating, low risk. I'll note this in my report."
```

---

### Pattern 2: Document Processing Tool

```python
from langchain.tools import tool
import PyPDF2
from typing import Dict

@tool
def parse_pdf(file_path: str) -> Dict[str, any]:
    """
    Extract text and metadata from a PDF document.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        dict with extracted text, page count, and metadata
    """
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        
        # Extract text from all pages
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        # Extract metadata
        metadata = pdf_reader.metadata
        
        return {
            "text": text,
            "page_count": len(pdf_reader.pages),
            "title": metadata.get('/Title', 'Unknown'),
            "author": metadata.get('/Author', 'Unknown'),
            "created_date": metadata.get('/CreationDate', 'Unknown'),
            "file_path": file_path
        }
```

**How the agent uses it:**
```
Agent thinks: "I need to read the SOC2 certificate"
Agent calls: parse_pdf("/uploads/acme_soc2.pdf")
Agent receives: {"text": "SOC 2 Type II Report...", "page_count": 45}
Agent thinks: "Now I'll classify this document"
```

---

### Pattern 3: RAG (Vector Search) Tool

```python
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone

# Initialize vector store
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("security-policies")
embeddings = OpenAIEmbeddings()

@tool
def search_security_policies(query: str, top_k: int = 5) -> list:
    """
    Search security policy database using semantic search.
    
    Args:
        query: Natural language query about security requirements
        top_k: Number of results to return (default 5)
        
    Returns:
        list of relevant policy excerpts with metadata
    """
    # Convert query to embedding
    query_embedding = embeddings.embed_query(query)
    
    # Search vector database
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )
    
    # Format results
    policies = []
    for match in results['matches']:
        policies.append({
            "policy_text": match['metadata']['text'],
            "policy_id": match['metadata']['policy_id'],
            "section": match['metadata']['section'],
            "relevance_score": match['score'],
            "last_updated": match['metadata']['updated_date']
        })
    
    return policies
```

**How the agent uses it:**
```
Agent thinks: "What are our security requirements for SaaS vendors?"
Agent calls: search_security_policies("SaaS vendor security requirements")
Agent receives: [
    {
        "policy_text": "All SaaS vendors must have SOC2 Type 2...",
        "relevance_score": 0.92
    },
    {
        "policy_text": "Penetration testing required within 12 months...",
        "relevance_score": 0.87
    }
]
Agent thinks: "So I need to check for SOC2 and recent pen test"
```

---

### Pattern 4: LLM-Powered Analysis Tool

```python
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

llm = ChatOpenAI(model="gpt-4", temperature=0)

@tool
def classify_document(text: str) -> Dict[str, any]:
    """
    Classify document type using LLM analysis.
    
    Args:
        text: Document text content
        
    Returns:
        dict with document type, confidence, and key details
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a document classification expert.
        Classify the document into one of these types:
        - SOC2_TYPE2
        - ISO27001
        - INSURANCE_CERTIFICATE
        - DATA_PROCESSING_AGREEMENT
        - FINANCIAL_STATEMENT
        - BUSINESS_CONTINUITY_PLAN
        - PENETRATION_TEST_REPORT
        - OTHER
        
        Also extract key details like expiration dates, coverage amounts, etc.
        Return JSON format."""),
        ("user", "Classify this document:\n\n{text}")
    ])
    
    # Truncate text if too long
    truncated_text = text[:4000] if len(text) > 4000 else text
    
    response = llm.invoke(prompt.format_messages(text=truncated_text))
    
    # Parse LLM response (assuming it returns JSON)
    import json
    result = json.loads(response.content)
    
    return {
        "document_type": result.get("type"),
        "confidence": result.get("confidence"),
        "key_details": result.get("details"),
        "expiration_date": result.get("expiration_date"),
        "issuer": result.get("issuer")
    }
```

**How the agent uses it:**
```
Agent has: text from parsed PDF
Agent thinks: "What type of document is this?"
Agent calls: classify_document(text)
Agent receives: {
    "document_type": "SOC2_TYPE2",
    "confidence": 0.95,
    "expiration_date": "2025-12-31"
}
Agent thinks: "It's a SOC2 report expiring in 2025"
```

---

### Pattern 5: Database Query Tool

```python
from langchain.tools import tool
import psycopg2
from typing import List, Dict

@tool
def get_required_documents(vendor_type: str, contract_value: str) -> List[str]:
    """
    Get list of required documents based on vendor type and contract value.
    
    Args:
        vendor_type: Type of vendor (e.g., "SaaS", "Hardware", "Consulting")
        contract_value: Contract value (e.g., "$100k", "$500k", "$1M+")
        
    Returns:
        list of required document types
    """
    # Connect to database
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    cursor = conn.cursor()
    
    # Query requirements table
    cursor.execute("""
        SELECT document_type, is_required, description
        FROM document_requirements
        WHERE vendor_type = %s 
        AND contract_value_min <= %s
        ORDER BY priority DESC
    """, (vendor_type, parse_contract_value(contract_value)))
    
    results = cursor.fetchall()
    
    required_docs = []
    for row in results:
        if row[1]:  # is_required
            required_docs.append({
                "document_type": row[0],
                "description": row[2]
            })
    
    cursor.close()
    conn.close()
    
    return required_docs
```

**How the agent uses it:**
```
Agent knows: vendor_type="SaaS", contract_value="$500k"
Agent thinks: "What documents do we need?"
Agent calls: get_required_documents("SaaS", "$500k")
Agent receives: [
    {"document_type": "SOC2_TYPE2", "description": "..."},
    {"document_type": "INSURANCE_CERTIFICATE", "description": "..."},
    {"document_type": "DPA", "description": "..."}
]
Agent thinks: "I need to check if these were submitted"
```

---

### Pattern 6: Email/Notification Tool

```python
from langchain.tools import tool
import sendgrid
from sendgrid.helpers.mail import Mail

sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)

@tool
def send_email(recipient: str, subject: str, body: str) -> Dict[str, any]:
    """
    Send email via SendGrid.
    
    Args:
        recipient: Email address of recipient
        subject: Email subject line
        body: Email body (HTML supported)
        
    Returns:
        dict with status and message_id
    """
    message = Mail(
        from_email='vendor-risk@company.com',
        to_emails=recipient,
        subject=subject,
        html_content=body
    )
    
    try:
        response = sg.send(message)
        
        return {
            "status": "sent",
            "status_code": response.status_code,
            "message_id": response.headers.get('X-Message-Id'),
            "recipient": recipient
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "recipient": recipient
        }
```

**How the agent uses it:**
```
Agent has: list of missing documents
Agent thinks: "I need to request these from the vendor"
Agent first calls: generate_evidence_request_email(gaps, vendor_contact)
Agent receives: email_body with professional request
Agent then calls: send_email("vendor@acme.com", "Missing Documents", email_body)
Agent receives: {"status": "sent", "message_id": "abc123"}
Agent thinks: "Email sent successfully, I'll create a follow-up task"
```

---

### Pattern 7: Calculation/Scoring Tool

```python
from langchain.tools import tool
from typing import Dict

@tool
def calculate_overall_risk_score(aggregated_data: Dict) -> Dict[str, any]:
    """
    Calculate weighted overall risk score from all review findings.
    
    Args:
        aggregated_data: dict containing security, compliance, financial scores
        
    Returns:
        dict with overall score, risk level, and breakdown
    """
    # Extract individual scores
    security_score = aggregated_data.get('security_score', 0)
    compliance_score = aggregated_data.get('compliance_score', 0)
    financial_score = aggregated_data.get('financial_score', 0)
    
    # Weighted calculation
    # Security: 40%, Compliance: 35%, Financial: 25%
    overall_score = (
        security_score * 0.40 +
        compliance_score * 0.35 +
        financial_score * 0.25
    )
    
    # Determine risk level
    if overall_score >= 80:
        risk_level = "Low"
        approval_tier = "manager"
    elif overall_score >= 60:
        risk_level = "Medium"
        approval_tier = "vp"
    elif overall_score >= 40:
        risk_level = "High"
        approval_tier = "executive"
    else:
        risk_level = "Critical"
        approval_tier = "board"
    
    return {
        "overall_score": round(overall_score, 2),
        "risk_level": risk_level,
        "approval_tier": approval_tier,
        "breakdown": {
            "security": security_score,
            "compliance": compliance_score,
            "financial": financial_score
        },
        "weights": {
            "security": "40%",
            "compliance": "35%",
            "financial": "25%"
        }
    }
```

**How the agent uses it:**
```
Agent has: all review reports
Agent thinks: "I need to calculate the overall risk"
Agent calls: calculate_overall_risk_score({
    "security_score": 85,
    "compliance_score": 78,
    "financial_score": 92
})
Agent receives: {
    "overall_score": 84.05,
    "risk_level": "Low",
    "approval_tier": "manager"
}
Agent thinks: "Low risk, manager approval needed"
```

---

### Pattern 8: External Security Scan Tool

```python
from langchain.tools import tool
import requests
import ssl
import socket
from urllib.parse import urlparse

@tool
def scan_domain_security(domain: str) -> Dict[str, any]:
    """
    Perform external security scan on vendor domain.
    
    Args:
        domain: Vendor domain name (e.g., "acme.com")
        
    Returns:
        dict with SSL rating, security headers, vulnerabilities
    """
    results = {}
    
    # 1. Check SSL/TLS configuration
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                results['ssl'] = {
                    "valid": True,
                    "version": ssock.version(),
                    "cipher": ssock.cipher()[0],
                    "expires": cert['notAfter']
                }
    except Exception as e:
        results['ssl'] = {"valid": False, "error": str(e)}
    
    # 2. Check security headers
    try:
        response = requests.get(f"https://{domain}", timeout=5)
        headers = response.headers
        
        results['security_headers'] = {
            "strict_transport_security": headers.get('Strict-Transport-Security', 'Missing'),
            "content_security_policy": headers.get('Content-Security-Policy', 'Missing'),
            "x_frame_options": headers.get('X-Frame-Options', 'Missing'),
            "x_content_type_options": headers.get('X-Content-Type-Options', 'Missing')
        }
        
        # Calculate header score
        present = sum(1 for v in results['security_headers'].values() if v != 'Missing')
        results['header_score'] = (present / 4) * 100
        
    except Exception as e:
        results['security_headers'] = {"error": str(e)}
    
    # 3. Check for common vulnerabilities (simplified)
    results['vulnerabilities'] = []
    
    if results['security_headers'].get('x_frame_options') == 'Missing':
        results['vulnerabilities'].append({
            "type": "Clickjacking",
            "severity": "Medium",
            "description": "Missing X-Frame-Options header"
        })
    
    # 4. Overall security score
    ssl_score = 100 if results['ssl'].get('valid') else 0
    header_score = results.get('header_score', 0)
    vuln_penalty = len(results['vulnerabilities']) * 10
    
    overall_score = max(0, (ssl_score * 0.5 + header_score * 0.5) - vuln_penalty)
    
    results['overall_security_score'] = round(overall_score, 2)
    
    return results
```

**How the agent uses it:**
```
Agent knows: vendor domain is "acme.com"
Agent thinks: "I should scan their security posture"
Agent calls: scan_domain_security("acme.com")
Agent receives: {
    "ssl": {"valid": True, "version": "TLSv1.3"},
    "security_headers": {"strict_transport_security": "max-age=31536000"},
    "vulnerabilities": [],
    "overall_security_score": 95
}
Agent thinks: "Strong security configuration, I'll note this positively"
```

---

## How Agents Decide Which Tools to Call

### The ReAct Loop

```python
# This is what happens inside the agent

# 1. REASON
Agent receives task: "Review Acme Corp security"
Agent thinks: "I need to:
  1. Check what security policies apply
  2. Validate any certificates they submitted
  3. Scan their domain
  4. Compile a report"

# 2. ACT
Agent calls: search_security_policies("SaaS vendor security requirements")

# 3. OBSERVE
Agent receives: [
    "SOC2 Type 2 required",
    "Penetration test within 12 months required"
]

# 4. REASON
Agent thinks: "They submitted a SOC2 cert, let me validate it"

# 5. ACT
Agent calls: validate_soc2_certificate(cert_data)

# 6. OBSERVE
Agent receives: {"valid": True, "expires": "2025-12-31"}

# 7. REASON
Agent thinks: "Good. Now let me scan their domain"

# 8. ACT
Agent calls: scan_domain_security("acme.com")

# 9. OBSERVE
Agent receives: {"overall_security_score": 95}

# 10. REASON
Agent thinks: "I have all the info. Time to generate report"

# 11. ACT
Agent calls: generate_security_report(all_findings)

# 12. OBSERVE
Agent receives: {"report": {...}, "score": 87}

# 13. REASON
Agent thinks: "Task complete. Returning report to supervisor."

# DONE
```

---

## Tool Registration with LangChain

```python
from langchain.agents import create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# Define all tools
tools = [
    search_security_policies,
    validate_soc2_certificate,
    validate_iso27001_certificate,
    check_certificate_expiry,
    scan_domain_security,
    check_breach_history,
    calculate_security_score,
    generate_security_report,
    flag_critical_issues
]

# Create agent with tools
llm = ChatOpenAI(model="gpt-4", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a security review specialist.
    Your goal is to thoroughly assess vendor security posture.
    
    You have access to tools for:
    - Searching security policies
    - Validating certificates
    - Scanning domains
    - Checking breach history
    - Generating reports
    
    Think step by step and use your tools to gather evidence."""),
    ("user", "{input}"),
    ("assistant", "{agent_scratchpad}")
])

security_agent = create_openai_functions_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

# The agent now knows about all tools and can call them autonomously
```

---

## Tool Execution Flow

```
User Request
    ↓
Supervisor Agent receives: "Review Acme Corp"
    ↓
Supervisor delegates to Security Agent
    ↓
Security Agent LLM thinks: "I need to check policies first"
    ↓
Security Agent calls tool: search_security_policies(...)
    ↓
Tool executes: Vector search in Pinecone
    ↓
Tool returns: List of relevant policies
    ↓
Security Agent LLM receives results
    ↓
Security Agent LLM thinks: "Now I need to validate their SOC2"
    ↓
Security Agent calls tool: validate_soc2_certificate(...)
    ↓
Tool executes: API call to validation service
    ↓
Tool returns: Validation result
    ↓
Security Agent LLM receives results
    ↓
... continues until task complete ...
    ↓
Security Agent returns report to Supervisor
```

---

## Key Points

1. **Tools are just Python functions** - They do specific tasks
2. **LLM decides when to call them** - Based on task and tool descriptions
3. **Tools return structured data** - JSON/dict format
4. **Agent loops until task complete** - Reason → Act → Observe → Repeat
5. **No hardcoded if/else** - Agent autonomously decides the flow
6. **Tools can call external APIs** - Databases, web services, etc.
7. **Tools can use other LLMs** - For analysis, classification, etc.
8. **Tools are composable** - One tool's output feeds another

---

## Example: Complete Agent Execution Trace

```
Task: "Review Acme Corp security"

[Agent Reasoning] I need to assess security. Let me start by checking requirements.
[Tool Call] search_security_policies("SaaS vendor security requirements")
[Tool Result] ["SOC2 Type 2 required", "Pen test within 12 months"]

[Agent Reasoning] They submitted a SOC2 cert. Let me validate it.
[Tool Call] validate_soc2_certificate(cert_data)
[Tool Result] {"valid": True, "expires": "2025-12-31", "type": "Type 2"}

[Agent Reasoning] Certificate is valid. Let me check expiration.
[Tool Call] check_certificate_expiry(cert_data)
[Tool Result] {"expired": False, "days_until_expiry": 612}

[Agent Reasoning] Good, not expired. Let me scan their domain.
[Tool Call] scan_domain_security("acme.com")
[Tool Result] {"ssl": "A+", "headers": "Good", "score": 95}

[Agent Reasoning] Strong security. Let me check breach history.
[Tool Call] check_breach_history("Acme Corp")
[Tool Result] {"breaches_found": 0, "last_checked": "2026-04-13"}

[Agent Reasoning] No breaches. Let me calculate the score.
[Tool Call] calculate_security_score({
    "soc2_valid": True,
    "domain_score": 95,
    "breaches": 0
})
[Tool Result] {"score": 87, "grade": "B+"}

[Agent Reasoning] I have all the data. Time to generate the report.
[Tool Call] generate_security_report(all_findings)
[Tool Result] {"report": {...}, "score": 87, "issues": []}

[Agent Reasoning] Task complete. Returning report.
[Return] Security assessment report with score 87/100
```

This is how tools work in autonomous agent systems!

