import { createTheme } from '@mantine/core';

export const theme = createTheme({
  primaryColor: 'green',
  defaultRadius: 'md',
  fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
  components: {
    // Touch-taugliche Mindestgrößen (Spezifikation 9.6).
    Button: { defaultProps: { size: 'md' } },
    TextInput: { defaultProps: { size: 'md' } },
    NumberInput: { defaultProps: { size: 'md' } },
    Select: { defaultProps: { size: 'md' } },
    PasswordInput: { defaultProps: { size: 'md' } },
  },
});
