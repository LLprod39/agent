export interface SSHJumpHost {
  host: string
  port?: number
  username: string
  password?: string
  private_key?: string
  passphrase?: string
}

export interface SSHConfig {
  host: string
  port?: number
  username: string
  password?: string
  private_key?: string
  passphrase?: string
  sudo_password?: string
  become_user?: string
  max_connection_attempts?: number
  known_hosts?: string[]
  labels?: Record<string, string>
  jump_host?: SSHJumpHost
}

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
  ssh?: SSHConfig
  extensions?: Record<string, any>
}

export interface EnvironmentListResponse {
  environments: Environment[]
  message: string
}

export interface EnvironmentResponse {
  environment: Environment
  message: string
}

export interface CreateEnvironmentRequest {
  id: string
  type: string
  display_name?: string
  description?: string
  networking: Record<string, any>
  auth: Record<string, any>
  policies: {
    risk_level: 'low' | 'medium' | 'high'
    require_approval: boolean
    change_ticket_required?: boolean
  }
  cluster?: Record<string, any>
  defaults?: Record<string, any>
  runbooks?: string[]
  notes?: string
  metadata?: Record<string, any>
  ssh?: SSHConfig
  extensions?: Record<string, any>
}

export type UpdateEnvironmentRequest = Partial<CreateEnvironmentRequest>





