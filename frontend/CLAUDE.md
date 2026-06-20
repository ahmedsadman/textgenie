# TextGenie (Frontend)

## Coding Style

- Always use proper Typescript types. Do NOT use `any` unless the proper fix gets too complicated

## Testing

- When writing RTL tests, always prefer testing user experience rather than testing implementation. **BAD:** `expect(onClick).toHaveBeenCalledWith(app)` — asserts a callback fired, not what the user sees. **GOOD:** Click the element, then assert the resulting UI: `expect(screen.getByText('expected content')).toBeInTheDocument()`.
