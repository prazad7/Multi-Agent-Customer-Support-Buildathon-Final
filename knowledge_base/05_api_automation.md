# API Test Automation

## 1. What is API Test Automation?

API test automation is the process of using software tools and code to
execute API test cases automatically.

API automation is useful for:

- Regression testing
- Repeated validation
- Data-driven testing
- Integration testing
- CI/CD pipelines
- Large API test suites
- Fast feedback during development

Automation should support good test design. Automating a poorly designed
test does not improve its quality.

---

## 2. When Should an API Test Be Automated?

API tests are good candidates for automation when they are:

- Frequently executed
- Stable
- Repetitive
- Business critical
- Deterministic
- Required for regression testing
- Required in CI/CD pipelines
- Expensive or time-consuming to execute manually

Examples:

- Login API regression
- User creation
- Order creation
- Payment validation
- Authentication scenarios
- Authorization scenarios
- API contract validation
- Critical business workflows

---

## 3. When Should an API Test Not Be Automated Immediately?

Automation may be delayed when:

- The API is changing frequently
- Requirements are unclear
- Expected behavior is unstable
- The test requires significant human judgment
- The test is rarely executed
- Automation maintenance cost is higher than its expected value

Automation decisions should consider risk, business value, execution
frequency, stability, and maintenance cost.

---

## 4. Python API Automation

Python can be used to automate HTTP API testing.

The `requests` library is commonly used to send HTTP requests.

Example:

```python
import requests

response = requests.get(
    "https://example.com/api/users/123"
)

print(response.status_code)
print(response.json())
5. GET Request Automation

Example:

import requests

response = requests.get(
    "https://example.com/api/users/123"
)

assert response.status_code == 200

A good test should validate more than the status code.

Additional validations can include:

Response body
Required fields
Data types
Business values
Response headers
Response schema

Example:

data = response.json()

assert data["id"] == 123
assert "name" in data
6. POST Request Automation

Example:

import requests

payload = {
    "name": "John",
    "email": "john@example.com"
}

response = requests.post(
    "https://example.com/api/users",
    json=payload
)

assert response.status_code == 201

Additional validations may include:

Generated resource ID
Response body
Required response fields
Persisted data
Business rules
7. PUT Request Automation

Example:

payload = {
    "name": "John Updated",
    "email": "john.updated@example.com"
}

response = requests.put(
    "https://example.com/api/users/123",
    json=payload
)

assert response.status_code == 200

Verify that:

The intended resource was updated.
The expected fields were changed.
Fields that should not change remain unchanged.
8. PATCH Request Automation

Example:

payload = {
    "email": "new@example.com"
}

response = requests.patch(
    "https://example.com/api/users/123",
    json=payload
)

assert response.status_code == 200

Verify that:

Requested fields were updated.
Unspecified fields remain unchanged where required.
Response follows the API contract.
9. DELETE Request Automation

Example:

response = requests.delete(
    "https://example.com/api/users/123"
)

assert response.status_code in [200, 204]

The expected status code must come from the API contract.

After deletion, verify that the resource behaves according to the
documented deletion behavior.

10. Request Headers

Headers can be supplied using a dictionary.

Example:

headers = {
    "Authorization": "Bearer <token>",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://example.com/api/users",
    headers=headers
)

Real credentials, tokens, and API keys must never be hard-coded in
automation source code.

11. Environment-Based Configuration

Environment-specific values should be separated from test logic.

Examples:

Base URL
API key
Username
Password
Client ID
Client secret
Environment name

Example:

import os

base_url = os.getenv("API_BASE_URL")
api_key = os.getenv("API_KEY")

Secrets should be stored securely and must not be committed to source
control.

12. Assertions

Assertions determine whether actual API behavior matches expected behavior.

Examples:

assert response.status_code == 200
assert response.json()["status"] == "ACTIVE"
assert "id" in response.json()
assert response.headers["Content-Type"].startswith("application/json")

Assertions should validate meaningful requirements.

Avoid tests that only verify that a request completed without actually
checking the expected behavior.

13. Response Body Validation

Response validation can include:

Required fields
Data types
Expected values
Nested objects
Arrays
Enumerations
Nullability
Business rules

Example:

data = response.json()

assert data["status"] == "ACTIVE"
assert isinstance(data["id"], int)
assert "email" in data
14. JSON Schema Validation

If an API has a defined JSON schema, automation can validate the response
against that schema.

Schema validation can verify:

Required properties
Property names
Data types
Nested structures
Arrays
Allowed values
String constraints
Numeric constraints

Schema validation helps detect API contract-breaking changes.

15. Negative API Automation

Negative scenarios should also be automated.

Example:

response = requests.post(
    "https://example.com/api/users",
    json={}
)

assert response.status_code == 400

Additional validations should verify the expected error structure.

Example:

data = response.json()

assert "error" in data

The expected response must be based on the API contract.

16. Authentication Automation

Authentication should preferably be handled through reusable utilities
rather than duplicated in every test.

Typical flow:

Authenticate
     ↓
Receive token
     ↓
Store token
     ↓
Use token in requests
     ↓
Execute API tests

Authentication logic should be separated from individual test cases.

17. Token Management

If access tokens expire during execution, the automation framework should
have a strategy for handling token renewal.

Possible approaches:

Authenticate before the test suite.
Authenticate before a test group.
Refresh the token when required.
Re-authenticate after expiration.

The correct approach depends on the authentication architecture.

18. Reusable API Client

Instead of duplicating HTTP request code, create reusable API client
methods.

Example:

class UserApi:

    def get_user(self, user_id):
        pass

    def create_user(self, payload):
        pass

    def update_user(self, user_id, payload):
        pass

    def delete_user(self, user_id):
        pass

Benefits:

Less duplication
Easier maintenance
Consistent request handling
Centralized authentication
Easier logging
Easier debugging
19. Test Layer and API Client Layer

A maintainable automation framework can separate responsibilities:

Test Case
    ↓
API Client
    ↓
HTTP Request
    ↓
API

The API client handles request construction.

The test handles validation and assertions.

20. Test Data Management

Test data should be separated from test logic where practical.

Possible sources include:

JSON
CSV
YAML
Database
Generated data
Environment configuration

Example:

payload = {
    "name": test_data["name"],
    "email": test_data["email"]
}

Test data should be deterministic when deterministic behavior is required.

21. Data-Driven API Testing

Data-driven testing executes the same test logic with multiple datasets.

Example:

Test Logic
    ↓
Valid email
Invalid email
Empty email
Malformed email
Duplicate email

Benefits:

Better coverage
Less duplicate test code
Easier expansion of test scenarios
22. Parameterized Testing

Testing frameworks such as pytest support parameterized testing.

Example:

@pytest.mark.parametrize(
    "status_code",
    [200, 400, 401, 403, 404]
)
def test_api(status_code):
    pass

The actual expected values must correspond to meaningful test scenarios.

23. Test Independence

API tests should be independent whenever possible.

Avoid unnecessary dependencies such as:

Test A creates user
       ↓
Test B updates user created by Test A
       ↓
Test C deletes user created by Test A

If Test A fails, Tests B and C may fail for unrelated reasons.

Better approaches include:

Independent setup
Dedicated test data
Fixtures
Controlled cleanup
API-level setup and teardown
24. Setup and Teardown

Setup may:

Create test data
Authenticate
Configure prerequisites

Teardown may:

Delete test data
Reset state
Clean temporary resources

The objective is to keep tests repeatable.

25. API Workflow Automation

Some business scenarios require multiple API calls.

Example:

Create User
     ↓
Login
     ↓
Create Order
     ↓
Retrieve Order
     ↓
Update Order
     ↓
Delete Order

Each important step should be validated instead of assuming that successful
execution of one request guarantees overall correctness.

26. Dynamic Data Handling

Some APIs return identifiers required by subsequent requests.

Example:

POST /users
     ↓
userId = 123
     ↓
GET /users/123

Automation should capture dynamic values from responses and use them in
subsequent requests.

Avoid hard-coding dynamic identifiers.

27. Logging

API automation should provide useful logs for troubleshooting.

Useful information includes:

Test case name
HTTP method
Endpoint
Request parameters
Request body where safe
Response status
Response body where safe
Execution time
Correlation ID

Sensitive information such as passwords, tokens, and API keys must never
be logged.

28. Failure Diagnostics

When an API test fails, the framework should provide enough information to
diagnose the failure.

Useful information includes:

Test name
Request
Expected result
Actual result
Status code
Response body
Relevant headers
Execution time
Correlation ID

Example of a useful failure:

Create User failed.

Expected status: 201
Actual status: 400

Error:
email field is required

Sensitive information must still be masked.

29. Retry Strategy

Retries should be used carefully.

Retries may be appropriate for:

Temporary network failures
Known transient infrastructure failures
Certain rate-limit scenarios

Retries should not hide genuine functional defects.

For example, repeatedly retrying a request that consistently returns 400
does not fix the functional problem.

Retry behavior should be:

Limited
Configurable
Logged
Applied only to appropriate failures
30. Timeout Handling

API automation should use explicit timeouts.

Example:

response = requests.get(
    "https://example.com/api/users",
    timeout=10
)

Timeout testing should distinguish between:

Connection timeout
API response timeout
Dependency timeout
31. CI/CD Integration

API automation can provide fast feedback when integrated into CI/CD.

Typical pipeline:

Developer Commit
       ↓
Build
       ↓
Unit Tests
       ↓
API Tests
       ↓
Test Report
       ↓
Deploy

API tests can be executed:

On every commit
On pull requests
During nightly regression
Before deployment
After deployment

The execution strategy should depend on test duration and business risk.

32. Test Reports

Automated API suites should generate useful reports.

A report may contain:

Total tests
Passed tests
Failed tests
Skipped tests
Execution duration
Failure details
33. API Automation Best Practices

Recommended practices:

Keep tests readable.
Use reusable API clients.
Separate configuration from test logic.
Store secrets outside source code.
Use meaningful assertions.
Validate response data, not only status codes.
Automate important negative scenarios.
Use parameterized testing where appropriate.
Keep tests independent.
Control test data.
Use explicit timeouts.
Use retries carefully.
Provide useful logs.
Mask sensitive information.
Integrate regression tests into CI/CD.
Keep automation maintainable.
34. API Automation Anti-Patterns

Avoid:

Hard-coded credentials.
Hard-coded access tokens.
Hard-coded environment URLs.
Excessive code duplication.
Assertions that only check HTTP 200.
Tests dependent on execution order.
Unlimited retries.
Shared test data without proper cleanup.
Logging sensitive credentials.
Large tests containing unrelated validations.
Ignoring intermittent failures without investigation.
35. QE Automation Decision Checklist

Before automating an API test, ask:

Is the behavior stable?
Is the scenario executed frequently?
Is it business critical?
Is the expected result deterministic?
Can the test be automated reliably?
Is the maintenance cost reasonable?
Can test data be controlled?
Can failures be diagnosed easily?
Can secrets be managed securely?
Will automation provide meaningful regression value?

Automation should maximize useful feedback rather than simply maximize the
number of automated tests.
