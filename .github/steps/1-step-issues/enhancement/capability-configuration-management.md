# Capability Configuration Management

Practice leads are hesitant to modify the capabilities directly in the code since they're concerned about breaking the system. We need to externalize the capability definitions for easier management.

## Proposed Solution

Move the list of consulting capabilities out of the Python file into a dedicated `capabilities.json` configuration file.

## Benefits

- Practice leads can safely update capability definitions without touching code
- Easier to add new capabilities as our consulting offerings expand
- Supports version control of capability changes
- Enables future integration with HR systems and certification tracking
- Reduces deployment dependencies when updating capability information

## Implementation Notes

The JSON structure should maintain all current capability attributes including practice areas, skill levels, certifications, industry verticals, and capacity information.
