using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace SvgToMp4.Core;

public sealed class JobStore
{
    private readonly string connectionString;
    private readonly object gate = new();
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    public JobStore(AppPaths paths)
    {
        connectionString = new SqliteConnectionStringBuilder { DataSource = Path.Combine(paths.Data, "studio.db"), DefaultTimeout = 10 }.ToString();
        using var db = Open();
        using var cmd = db.CreateCommand();
        cmd.CommandText = "PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, created TEXT NOT NULL, payload TEXT NOT NULL);";
        cmd.ExecuteNonQuery();
        foreach (var job in List().Where(j => !JobStates.Terminal(j.State) && j.State != "Queued"))
            Update(job.Id, j => j with { State = "Failed", Stage = "Đã gián đoạn", Error = "Ứng dụng đã dừng trong lúc xử lý. Bạn có thể tạo lại tác vụ." });
    }
    private SqliteConnection Open() { var c = new SqliteConnection(connectionString); c.Open(); return c; }
    public IReadOnlyList<Job> List()
    {
        lock (gate)
        {
            using var db = Open(); using var cmd = db.CreateCommand();
            cmd.CommandText = "SELECT payload FROM jobs ORDER BY created DESC LIMIT 200";
            using var r = cmd.ExecuteReader(); var jobs = new List<Job>();
            while (r.Read()) jobs.Add(JsonSerializer.Deserialize<Job>(r.GetString(0), Json)!);
            return jobs;
        }
    }
    public Job? Get(string id)
    {
        lock (gate)
        {
            using var db = Open(); using var cmd = db.CreateCommand();
            cmd.CommandText = "SELECT payload FROM jobs WHERE id=$id"; cmd.Parameters.AddWithValue("$id", id);
            return cmd.ExecuteScalar() is string s ? JsonSerializer.Deserialize<Job>(s, Json) : null;
        }
    }
    public void Add(Job job)
    {
        lock (gate)
        {
            using var db = Open(); using var cmd = db.CreateCommand();
            cmd.CommandText = "INSERT INTO jobs(id,created,payload) VALUES($id,$created,$payload)";
            cmd.Parameters.AddWithValue("$id", job.Id); cmd.Parameters.AddWithValue("$created", job.CreatedAt);
            cmd.Parameters.AddWithValue("$payload", JsonSerializer.Serialize(job, Json)); cmd.ExecuteNonQuery();
        }
    }
    public Job? Update(string id, Func<Job, Job> change)
    {
        lock (gate)
        {
            var job = Get(id); if (job is null) return null;
            var updated = change(job) with { UpdatedAt = DateTimeOffset.UtcNow.ToString("O") };
            using var db = Open(); using var cmd = db.CreateCommand();
            cmd.CommandText = "UPDATE jobs SET payload=$payload WHERE id=$id";
            cmd.Parameters.AddWithValue("$id", id); cmd.Parameters.AddWithValue("$payload", JsonSerializer.Serialize(updated, Json));
            cmd.ExecuteNonQuery(); return updated;
        }
    }
}
