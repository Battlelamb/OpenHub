import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface ResponsiveListProps {
  children: ReactNode
  className?: string
}

interface ResponsiveListHeaderProps {
  children: ReactNode
  className?: string
}

interface ResponsiveListRowProps {
  children: ReactNode
  className?: string
}

interface ResponsiveListCellProps {
  children: ReactNode
  className?: string
  header?: boolean
}

function ResponsiveListHeader({ children, className }: ResponsiveListHeaderProps) {
  return (
    <thead className={cn('hidden md:table-header-group', className)}>
      {children}
    </thead>
  )
}

function ResponsiveListRow({ children, className }: ResponsiveListRowProps) {
  return (
    <>
      <tr className={cn('hidden md:table-row', className)}>{children}</tr>
      <div className={cn('block md:hidden', className)}>
        {children}
      </div>
    </>
  )
}

function ResponsiveListCell({ children, className, header }: ResponsiveListCellProps) {
  return (
    <>
      <td className={cn('hidden md:table-cell', className)}>{children}</td>
      {header && <div className={cn('md:hidden text-xs font-medium text-zinc-400', className)}>{children}</div>}
      {!header && <div className={cn('md:hidden', className)}>{children}</div>}
    </>
  )
}

export function ResponsiveList({ children, className }: ResponsiveListProps) {
  return (
    <div className={cn('w-full', className)}>
      <table className="w-full md:table table-fixed">{children}</table>
    </div>
  )
}

ResponsiveList.Header = ResponsiveListHeader
ResponsiveList.Row = ResponsiveListRow
ResponsiveList.Cell = ResponsiveListCell
