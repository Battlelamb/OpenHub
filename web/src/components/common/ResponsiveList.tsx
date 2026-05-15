import { Children, isValidElement, ReactElement, ReactNode } from 'react'
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

type ResponsiveListElement<P> = ReactElement<P>

function ResponsiveListHeader(_props: ResponsiveListHeaderProps) {
  return null
}

function ResponsiveListRow(_props: ResponsiveListRowProps) {
  return null
}

function ResponsiveListCell(_props: ResponsiveListCellProps) {
  return null
}

function isHeaderElement(node: ReactNode): node is ResponsiveListElement<ResponsiveListHeaderProps> {
  return isValidElement(node) && node.type === ResponsiveListHeader
}

function isRowElement(node: ReactNode): node is ResponsiveListElement<ResponsiveListRowProps> {
  return isValidElement(node) && node.type === ResponsiveListRow
}

function isCellElement(node: ReactNode): node is ResponsiveListElement<ResponsiveListCellProps> {
  return isValidElement(node) && node.type === ResponsiveListCell
}

function renderDesktopCells(row: ResponsiveListElement<ResponsiveListRowProps>) {
  return Children.toArray(row.props.children)
    .filter(isCellElement)
    .map((cell, index) => (
      <td key={cell.key ?? index} className={cn('py-3 px-4', cell.props.className)}>
        {cell.props.children}
      </td>
    ))
}

function renderMobileCells(row: ResponsiveListElement<ResponsiveListRowProps>) {
  return Children.toArray(row.props.children)
    .filter(isCellElement)
    .map((cell, index) => (
      <div
        key={cell.key ?? index}
        className={cn(
          cell.props.header ? 'text-sm font-medium text-zinc-100' : 'text-sm text-zinc-400',
          cell.props.className,
        )}
      >
        {cell.props.children}
      </div>
    ))
}

export function ResponsiveList({ children, className }: ResponsiveListProps) {
  const childArray = Children.toArray(children)
  const headers = childArray.filter(isHeaderElement)
  const rows = childArray.filter(isRowElement)

  return (
    <div className={cn('w-full', className)}>
      <table className="hidden w-full table-fixed md:table">
        {headers.map((header, index) => (
          <thead key={header.key ?? index} className={cn('table-header-group', header.props.className)}>
            {header.props.children}
          </thead>
        ))}
        <tbody>
          {rows.map((row, index) => (
            <tr key={row.key ?? index} className={cn('table-row', row.props.className)}>
              {renderDesktopCells(row)}
            </tr>
          ))}
        </tbody>
      </table>
      <div data-responsive-list-mobile className="space-y-3 md:hidden">
        {rows.map((row, index) => (
          <div key={row.key ?? index} className={cn('rounded-lg border border-zinc-800 bg-zinc-900 p-4', row.props.className)}>
            {renderMobileCells(row)}
          </div>
        ))}
      </div>
    </div>
  )
}

ResponsiveList.Header = ResponsiveListHeader
ResponsiveList.Row = ResponsiveListRow
ResponsiveList.Cell = ResponsiveListCell
