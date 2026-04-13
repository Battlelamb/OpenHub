import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateTask } from '@/hooks/queries/useTasks'
import { useAgents } from '@/hooks/queries/useAgents'

const schema = z.object({
  title: z.string().min(1, 'Title required'),
  description: z.string().optional(),
  priority: z.number().min(1).max(5).default(3),
  agent_id: z.string().optional().nullable(),
  required_capabilities: z.array(z.string()).optional(),
})

type TaskFormValues = z.infer<typeof schema>

interface TaskCreateFormProps {
  onSuccess?: () => void
}

export function TaskCreateForm({ onSuccess }: TaskCreateFormProps) {
  const { t } = useTranslation('tasks')
  const createTask = useCreateTask()
  const { data: agents } = useAgents()

  const form = useForm<TaskFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: '',
      description: '',
      priority: 3,
      agent_id: null,
      required_capabilities: [],
    },
  })

  const onSubmit = async (values: TaskFormValues) => {
    try {
      await createTask.mutateAsync(values)
      toast.success('Task created')
      form.reset()
      onSuccess?.()
    } catch {
      toast.error('Failed to create task')
    }
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>{t('createCta')}</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('dialogTitle')}</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('fields.title')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('fields.description')}</FormLabel>
                  <FormControl>
                    <Textarea {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="priority"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('fields.priority')}</FormLabel>
                  <Select
                    onValueChange={(v) => field.onChange(Number.parseInt(v))}
                    defaultValue={String(field.value)}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="1">1 (Low)</SelectItem>
                      <SelectItem value="2">2</SelectItem>
                      <SelectItem value="3">3 (Normal)</SelectItem>
                      <SelectItem value="4">4</SelectItem>
                      <SelectItem value="5">5 (High)</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="agent_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('fields.agent')}</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value ?? ''}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Any agent" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="">Any agent</SelectItem>
                      {agents?.map((agent) => (
                        <SelectItem key={agent.id} value={agent.id}>
                          {agent.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={form.formState.isSubmitting}>
              {t('dispatchCta')}
            </Button>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
