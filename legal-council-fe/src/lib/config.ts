export const config = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
    timeout: 10000,
  },
} as const;
