import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { API_URL } from '../config';
import type { Project } from '../types';

const formSchema = z.object({
  projectId: z.number({
    message: 'Please select a project',
  }),
  duration: z.number({
    message: 'Please enter a duration',
  }).min(1, 'Duration must be at least 1 minute'),
});

type FormValues = z.infer<typeof formSchema>;

export default function LogSession() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      projectId: undefined,
      duration: undefined,
    },
  });

  useEffect(() => {
    fetch(`${API_URL}/projects`)
      .then((response) => response.json())
      .then((data) => {
        setProjects(data);
        setProjectsLoading(false);
      })
      .catch((error) => {
        console.error('Error fetching projects:', error);
        setProjectsLoading(false);
        toast.error('Failed to load projects');
      });
  }, []);

  const onSubmit = async (values: FormValues) => {
    const now = new Date();
    const startTime = new Date(now.getTime() - values.duration * 60 * 1000);

    try {
      const response = await fetch(`${API_URL}/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: values.projectId,
          start_time: startTime.toISOString(),
          end_time: now.toISOString(),
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
                      {project.name}
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
