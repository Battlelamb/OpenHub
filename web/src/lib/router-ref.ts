import type { Router } from '@tanstack/react-router'

let routerRef: Router<any, any> | null = null

export function setRouter(r: Router<any, any>) {
  routerRef = r
}

export function getRouter(): Router<any, any> | null {
  return routerRef
}
