{{- define "medislot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "medislot.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else if contains (include "medislot.name" .) .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name (include "medislot.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "medislot.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/part-of: medislot
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}

{{/* Selector labels for one component: include "medislot.selectorLabels" (list . "backend") */}}
{{- define "medislot.selectorLabels" -}}
{{- $root := index . 0 -}}
app.kubernetes.io/name: {{ include "medislot.name" $root }}
app.kubernetes.io/instance: {{ $root.Release.Name }}
app.kubernetes.io/component: {{ index . 1 }}
{{- end }}

{{- define "medislot.componentName" -}}
{{- printf "%s-%s" (include "medislot.fullname" (index . 0)) (index . 1) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "medislot.image" -}}
{{- $root := index . 0 -}}
{{- $image := index . 1 -}}
{{- printf "%s:%s" $image.repository (default $root.Chart.AppVersion $image.tag) }}
{{- end }}

{{- define "medislot.dbSecretName" -}}
{{- if .Values.postgresql.auth.existingSecret }}
{{- .Values.postgresql.auth.existingSecret }}
{{- else }}
{{- include "medislot.componentName" (list . "db") }}
{{- end }}
{{- end }}

{{- define "medislot.dbHost" -}}
{{- include "medislot.componentName" (list . "postgres") }}
{{- end }}

{{/* Env vars shared by the API container and the migration init container. */}}
{{- define "medislot.backendEnv" -}}
- name: DB_USER
  valueFrom:
    secretKeyRef:
      name: {{ include "medislot.dbSecretName" . }}
      key: username
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "medislot.dbSecretName" . }}
      key: password
- name: DATABASE_URL
  value: "postgresql+psycopg://$(DB_USER):$(DB_PASSWORD)@{{ include "medislot.dbHost" . }}:5432/{{ .Values.postgresql.database }}"
- name: APP_VERSION
  value: {{ default .Chart.AppVersion .Values.backend.image.tag | quote }}
- name: ENVIRONMENT
  value: {{ .Values.environment | quote }}
- name: LOG_LEVEL
  value: {{ .Values.backend.logLevel | quote }}
{{- end }}
