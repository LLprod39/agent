export interface Environment {
  id: string
  display_name: string
  type: string
  metadata?: {
    region?: string
    owner?: string
  }
  cluster?: {
    name?: string
    context?: string
  }
  networking?: {
    proxy?: {
      http?: string
      https?: string
      no_proxy?: string
    }
    bastion?: string
    allowed_endpoints?: string[]
  }
  auth?: {
    vault_role?: string
    service_account?: string
    ssh_cert_role?: string
  }
  policies?: {
    risk_level?: 'low' | 'medium' | 'high'
    require_approval?: boolean
  }
  defaults?: {
    namespace?: string
    package_manager?: string
  }
  runbooks?: string[]
  notes?: string
}

export interface EnvironmentListResponse {
  environments: Environment[]
  message: string
}

export interface EnvironmentResponse {
  environment: Environment
  message: string
}





