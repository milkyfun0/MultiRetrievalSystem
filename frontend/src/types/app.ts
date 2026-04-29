export type ServiceStatus = 'unknown' | 'healthy' | 'degraded' | 'error'

export interface HealthResponseDTO {
  status: string
  services?: {
    api?: boolean
    faiss?: boolean
    minio?: boolean
    algorithm?: boolean
  }
}
