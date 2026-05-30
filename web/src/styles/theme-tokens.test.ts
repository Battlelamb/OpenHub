/// <reference types="node" />

import { readFileSync } from 'node:fs'

const css = readFileSync(`${process.cwd()}/src/index.css`, 'utf8')

const requiredSemanticTokens = [
  'background',
  'foreground',
  'card',
  'card-foreground',
  'popover',
  'popover-foreground',
  'primary',
  'primary-foreground',
  'secondary',
  'secondary-foreground',
  'muted',
  'muted-foreground',
  'accent',
  'accent-foreground',
  'destructive',
  'destructive-foreground',
  'border',
  'input',
  'ring',
]

describe('Tailwind semantic color tokens', () => {
  it('exposes every shadcn semantic token used by shared overlay components', () => {
    for (const token of requiredSemanticTokens) {
      expect(css).toContain(`--color-${token}: hsl(var(--${token}));`)
    }
  })
})
