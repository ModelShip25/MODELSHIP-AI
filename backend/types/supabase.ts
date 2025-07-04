export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      analytics: {
        Row: {
          created_at: string | null
          id: number
          metric_data: Json | null
          metric_type: string
          metric_value: number
          period_end: string
          period_start: string
          project_id: number | null
          user_id: number | null
        }
        Insert: {
          created_at?: string | null
          id?: number
          metric_data?: Json | null
          metric_type: string
          metric_value: number
          period_end: string
          period_start: string
          project_id?: number | null
          user_id?: number | null
        }
        Update: {
          created_at?: string | null
          id?: number
          metric_data?: Json | null
          metric_type?: string
          metric_value?: number
          period_end?: string
          period_start?: string
          project_id?: number | null
          user_id?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "analytics_project_id_fkey"
            columns: ["project_id"]
            isOneToOne: false
            referencedRelation: "projects"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "analytics_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      annotations: {
        Row: {
          class_name: string
          confidence: number
          created_at: string | null
          id: string
          image_id: string
          updated_at: string | null
          user_id: string | null
          x_max: number
          x_min: number
          y_max: number
          y_min: number
        }
        Insert: {
          class_name: string
          confidence: number
          created_at?: string | null
          id?: string
          image_id: string
          updated_at?: string | null
          user_id?: string | null
          x_max: number
          x_min: number
          y_max: number
          y_min: number
        }
        Update: {
          class_name?: string
          confidence?: number
          created_at?: string | null
          id?: string
          image_id?: string
          updated_at?: string | null
          user_id?: string | null
          x_max?: number
          x_min?: number
          y_max?: number
          y_min?: number
        }
        Relationships: [
          {
            foreignKeyName: "annotations_image_id_fkey"
            columns: ["image_id"]
            isOneToOne: false
            referencedRelation: "images"
            referencedColumns: ["id"]
          },
        ]
      }
      images: {
        Row: {
          content_type: string
          created_at: string | null
          file_hash: string
          filename: string
          height: number | null
          id: string
          preview_path: string | null
          size: number
          status: string | null
          storage_path: string
          stored_filename: string
          updated_at: string | null
          user_id: string | null
          width: number | null
        }
        Insert: {
          content_type: string
          created_at?: string | null
          file_hash: string
          filename: string
          height?: number | null
          id?: string
          preview_path?: string | null
          size: number
          status?: string | null
          storage_path: string
          stored_filename: string
          updated_at?: string | null
          user_id?: string | null
          width?: number | null
        }
        Update: {
          content_type?: string
          created_at?: string | null
          file_hash?: string
          filename?: string
          height?: number | null
          id?: string
          preview_path?: string | null
          size?: number
          status?: string | null
          storage_path?: string
          stored_filename?: string
          updated_at?: string | null
          user_id?: string | null
          width?: number | null
        }
        Relationships: []
      }
      jobs: {
        Row: {
          completed_at: string | null
          completed_items: number | null
          error_message: string | null
          id: string
          job_type: string
          metadata: Json | null
          status: string | null
          total_items: number | null
          user_id: string | null
          created_at: string | null
          updated_at: string | null
        }
        Insert: {
          completed_at?: string | null
          completed_items?: number | null
          error_message?: string | null
          id?: string
          job_type: string
          metadata?: Json | null
          status?: string | null
          total_items?: number | null
          user_id?: string | null
          created_at?: string | null
          updated_at?: string | null
        }
        Update: {
          completed_at?: string | null
          completed_items?: number | null
          error_message?: string | null
          id?: string
          job_type?: string
          metadata?: Json | null
          status?: string | null
          total_items?: number | null
          user_id?: string | null
          created_at?: string | null
          updated_at?: string | null
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DefaultSchema = Database[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

// ModelShip specific types
export type Image = Tables<"images">
export type Annotation = Tables<"annotations">
export type Job = Tables<"jobs">

export type ImageInsert = TablesInsert<"images">
export type AnnotationInsert = TablesInsert<"annotations">
export type JobInsert = TablesInsert<"jobs">

export type ImageUpdate = TablesUpdate<"images">
export type AnnotationUpdate = TablesUpdate<"annotations">
export type JobUpdate = TablesUpdate<"jobs"> 