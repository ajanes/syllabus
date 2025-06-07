defmodule Syllabus.Application do
  # See https://hexdocs.pm/elixir/Application.html
  # for more information on OTP Applications
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      SyllabusWeb.Telemetry,
      {DNSCluster, query: Application.get_env(:syllabus, :dns_cluster_query) || :ignore},
      {Phoenix.PubSub, name: Syllabus.PubSub},
      # Start the Finch HTTP client for sending emails
      {Finch, name: Syllabus.Finch},
      # Start a worker by calling: Syllabus.Worker.start_link(arg)
      # {Syllabus.Worker, arg},
      # Start to serve requests, typically the last entry
      SyllabusWeb.Endpoint
    ]

    # See https://hexdocs.pm/elixir/Supervisor.html
    # for other strategies and supported options
    opts = [strategy: :one_for_one, name: Syllabus.Supervisor]
    Supervisor.start_link(children, opts)
  end

  # Tell Phoenix to update the endpoint configuration
  # whenever the application is updated.
  @impl true
  def config_change(changed, _new, removed) do
    SyllabusWeb.Endpoint.config_change(changed, removed)
    :ok
  end
end
