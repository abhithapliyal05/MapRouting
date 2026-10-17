{{/* Labels applied to every object */}}
{{- define "routing.labels" -}}
app.kubernetes.io/name: routing
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/* Selector labels for one component: pass (dict "root" . "component" "astar") */}}
{{- define "routing.selector" -}}
app.kubernetes.io/name: routing
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/* Name of the shared data claim */}}
{{- define "routing.dataClaim" -}}
{{ .Release.Name }}-map-data
{{- end }}
