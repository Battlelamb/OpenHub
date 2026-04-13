// Top-level composition root reserved for providers that can't live in main.tsx.
// For now, App is not mounted; main.tsx uses RouterProvider directly.
// Plan 03 (auth) and Plan 04 (data) may wrap the RouterProvider here.
export {}
