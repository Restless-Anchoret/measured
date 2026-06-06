import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { CalendarIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import ColorDot from '@/components/ColorDot';
import { API_URL } from '../config';
import { useProjects } from '../hooks/useProjects';
import { useEffect } from 'react';

const formSchema = z.object({
  projectId: z.number({
    message: 'Please select a project',
  }),
  duration: z.number({
    message: 'Please enter a duration',
  }).min(1, 'Duration must be at least 1 minute'),
  date: z.date(),
});

type FormValues = z.infer<typeof formSchema>;

export default function LogSession() {
  const { projects, loading: projectsLoading, error: projectsError } = useProjects();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      projectId: undefined,
      duration: undefined,
      date: new Date(),
    },
  });

  useEffect(() => {
    if (projectsError) {
      toast.error('Failed to load projects');
    }
  }, [projectsError]);

  const onSubmit = async (values: FormValues) => {
    const now = new Date();
    const isToday =
      values.date.getFullYear() === now.getFullYear() &&
      values.date.getMonth() === now.getMonth() &&
      values.date.getDate() === now.getDate();

    let startTime: Date;
    let endTime: Date;
    if (isToday) {
      endTime = now;
      startTime = new Date(now.getTime() - values.duration * 60 * 1000);
    } else {
      startTime = new Date(values.date);
      startTime.setHours(10, 0, 0, 0);
      endTime = new Date(startTime.getTime() + values.duration * 60 * 1000);
    }

    try {
      const response = await fetch(`${API_URL}/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: values.projectId,
          start_time: startTime.toISOString(),
          end_time: endTime.toISOString(),
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to log session');
      }

      toast.success('New session logged');

      // Clear form on success
      form.reset();
    } catch {
      toast.error('Failed to log session');
    }
  };

  return (
    <div>
      <h1 className="text-4xl font-bold mb-6">Log Session</h1>
      <Form form={form} onSubmit={onSubmit} className="max-w-md space-y-6">
        <FormField
          control={form.control}
          name="projectId"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Project</FormLabel>
              <Select
                onValueChange={(value) => field.onChange(Number(value))}
                value={field.value?.toString()}
                disabled={projectsLoading}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a project" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {projects.map((project) => (
                    <SelectItem key={project.id} value={String(project.id)}>
                      <span className="flex items-center gap-2">
                        <ColorDot color={project.color} extraColor={project.extraColor} />
                        {project.name}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="duration"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Duration (minutes)</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  placeholder="Enter duration in minutes"
                  {...field}
                  value={field.value ?? ''}
                  onChange={(e) => {
                    const value = e.target.value;
                    field.onChange(value === '' ? undefined : Number(value));
                  }}
                  min={1}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="date"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Date</FormLabel>
              <Popover>
                <PopoverTrigger asChild>
                  <FormControl>
                    <Button
                      variant="outline"
                      className={cn('w-full justify-start text-left font-normal')}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {format(field.value, 'PPP')}
                    </Button>
                  </FormControl>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={field.value}
                    onSelect={(d) => d && field.onChange(d)}
                  />
                </PopoverContent>
              </Popover>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button
          type="submit"
          className="w-full"
          disabled={form.formState.isSubmitting || projectsLoading}
        >
          {form.formState.isSubmitting ? 'Logging...' : 'Log Session'}
        </Button>
      </Form>
    </div>
  );
}
