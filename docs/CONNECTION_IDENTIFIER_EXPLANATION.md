# Connection Identifier Explanation

## What is `connection_identifier`?

The `connection_identifier` is an **optional parameter** that helps you specify which patient/connection to use when your LibreLinkUp account follows multiple patients.

## When do you need it?

LibreLinkUp allows you to follow multiple patients (e.g., family members, dependents). When your account follows more than one patient, the client needs to know which one to retrieve data from.

## How it works (from original TypeScript code)

Looking at `libre-link-up-api-client/src/client.ts` lines 143-170:

```typescript
const getConnection = (connections: Datum[]): string => {
  // If connectionIdentifier is a STRING (patient name)
  if (typeof connectionIdentifier === 'string') {
    // Find connection by matching full name
    const match = connections.find(
      ({ firstName, lastName }) =>
        `${firstName} ${lastName}`.toLowerCase() ===
        connectionIdentifier.toLowerCase()
    );
    return match.patientId;
  }
  
  // If connectionIdentifier is a FUNCTION
  if (typeof connectionIdentifier === 'function') {
    // Use custom function to find connection
    return connectionIdentifier.call(null, connections);
  }
  
  // DEFAULT: If undefined/null, use the FIRST connection
  return connections[0].patientId;
};
```

## Acceptable Values

### ✅ `null` or `undefined` (RECOMMENDED if you follow only one patient)
- **Behavior**: Automatically uses the **first connection** in the list
- **Use case**: When you follow only one patient, or want to use the default

```yaml
connection_identifier: null  # ✓ Perfectly acceptable!
```

### ✅ String (Patient's full name)
- **Behavior**: Finds connection by matching first name + last name
- **Use case**: When you follow multiple patients and want to specify which one

```yaml
connection_identifier: "John Doe"  # Must match exactly: firstName + " " + lastName
```

### ✅ Function (Advanced - Python only, not in YAML)
- **Behavior**: Custom logic to select connection
- **Use case**: Complex selection logic (e.g., by patient ID, criteria, etc.)

```python
def select_connection(connections):
    for conn in connections:
        if conn['firstName'] == 'John':
            return conn['patientId']
    return None

client = LibreLinkUpClient(
    username="...",
    password="...",
    connection_identifier=select_connection  # Custom function
)
```

## Is `null` acceptable?

**YES! `null` is perfectly acceptable and is the recommended default.**

According to the original TypeScript code (line 169):
- If `connectionIdentifier` is `undefined`, `null`, or not provided
- The client will use `connections[0].patientId` (the first connection)

This means:
- ✅ `null` = Use first connection automatically
- ✅ Most users only need `null` (if following one patient)
- ✅ Safe default that works for single-patient accounts

## Example Scenarios

### Scenario 1: Following One Patient (Most Common)
```yaml
connection_identifier: null  # ✓ Use the only connection
```

### Scenario 2: Following Multiple Patients - By Name
```yaml
connection_identifier: "Ivan Petrov"  # ✓ Specific patient
```

### Scenario 3: Following Multiple Patients - Default
```yaml
connection_identifier: null  # ✓ Use first in list (might vary)
```

## Python Implementation

The Python client follows the same logic (see `libre_link_up_client/client.py` lines 192-218):

```python
def _get_connection_id(self, connections):
    if isinstance(self.connection_identifier, str):
        # Find by name
        ...
    elif callable(self.connection_identifier):
        # Use function
        ...
    else:
        # DEFAULT: Use first connection
        return connections[0]['patientId']
```

## Summary

| Value | Behavior | When to Use |
|-------|----------|-------------|
| `null` | Uses first connection | ✅ **Recommended** - Following one patient or want default |
| `"Name"` | Matches by full name | Following multiple patients, need specific one |
| Function | Custom selection logic | Advanced use cases (Python code only) |

**Your current config with `null` is perfect!** ✅

