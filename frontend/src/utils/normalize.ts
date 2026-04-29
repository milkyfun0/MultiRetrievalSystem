export function splitLinesToItems(text: string): string[] {
  return text
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function truncateMiddle(value: string, left = 16, right = 10): string {
  if (value.length <= left + right + 3) {
    return value
  }
  return `${value.slice(0, left)}...${value.slice(-right)}`
}
