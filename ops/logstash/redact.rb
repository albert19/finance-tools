# Logstash Ruby filter. Defense in depth: apps must NOT log secrets in the first
# place. Recursively sanitize parsed JSON and raw message before indexing.
def register(params)
  @secret_key = /(?:authorization|cookie|password|passwd|secret|token|api[_-]?key|private[_-]?key|credential|database_url)/i
  @embedded = /(?:Bearer\s+)[a-z0-9._~+\/-]+|(?:authorization|cookie|password|passwd|secret|token|api[_-]?key|private[_-]?key|credential|database_url)\s*[:=]\s*(?:"[^"]*"|'[^']*'|[^\s,&;]+)/i
end

def scrub(value, key = nil)
  return "[REDACTED]" if key && @secret_key.match?(key.to_s)
  case value
  when Hash
    value.each_with_object({}) { |(k, v), h| h[k] = scrub(v, k) }
  when Array
    value.map { |v| scrub(v) }
  when String
    value.gsub(@embedded, "[REDACTED]")
  else
    value
  end
end

def filter(event)
  event.to_hash.each { |key, value| event.set(key, scrub(value, key)) }
  [event]
end
