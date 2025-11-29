export const config = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || 'https://legal-council-api-820608432774.asia-southeast2.run.app/api/v1',
    timeout: 30000,
  },
} as const;
