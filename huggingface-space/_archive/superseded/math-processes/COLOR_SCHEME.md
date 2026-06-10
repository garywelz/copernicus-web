# Mathematics Process Color Scheme

**5-Color Rule for Mathematics Flowcharts**

Following the Programming Framework's standard color system:

## Color Categories

1. **Red (#ff6b6b)** - Triggers & Inputs
   - Initial conditions
   - Environmental inputs
   - Starting materials
   - Data inputs
   - **Text color:** White (#fff)

2. **Yellow (#ffd43b)** - Structures & Objects
   - Physical structures
   - Molecules
   - Data structures
   - Algorithms
   - Logical constructs
   - **Text color:** Black (#000) for readability

3. **Green (#51cf66)** - Processing & Operations
   - Transformations
   - Reactions
   - Computations
   - Operations that change state
   - **Text color:** White (#fff)

4. **Blue (#74c0fc)** - Intermediates & States
   - Intermediate products
   - Temporary states
   - Transitional conditions
   - **Text color:** White (#fff)

5. **Violet/Purple (#b197fc)** - Products & Outputs
   - Final outputs
   - End products
   - Results
   - **Text color:** White (#fff)

## Gate Detection

**AND Gates:** Nodes with 2 or more incoming edges
- Represents convergence of multiple paths
- Example: A result that requires multiple conditions to be met

**OR Gates:** Nodes with 1 incoming edge and 2 or more outgoing edges
- Represents branching/decision points
- Example: A condition that leads to multiple possible outcomes

## Mermaid Style Syntax

```mermaid
style NodeID fill:#COLOR,color:#TEXTCOLOR
```

Examples:
- `style A1 fill:#ff6b6b,color:#fff` (Red trigger)
- `style B1 fill:#ffd43b,color:#000` (Yellow structure)
- `style C1 fill:#51cf66,color:#fff` (Green operation)
- `style D1 fill:#74c0fc,color:#fff` (Blue intermediate)
- `style E1 fill:#b197fc,color:#fff` (Purple output)
```

