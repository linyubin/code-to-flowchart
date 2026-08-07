using System;
using System.Timers;

namespace OrderImportExample
{
    // Fictional example service. Polls a legacy file-watcher for incoming
    // order files once a second, parses them, and upserts them into a
    // database. Representative of a common legacy shape: a self-re-arming
    // polling timer whose handler has grown into a single large method with
    // near-per-statement try/catch and a duplicated old-format/new-format
    // branch. In a real 500-line version of this pattern, the try/catch
    // wrapping shown on a few statements here typically repeats on nearly
    // every line — trimmed here for readability.
    public class OrderImportWorker
    {
        private Timer _pollTimer;
        private WatcherConnection _connection;
        private bool _pingStatus;

        public void StartOperation()
        {
            try
            {
                _pollTimer = new Timer();
                _pollTimer.Interval = 1000;
                _pollTimer.Elapsed += new ElapsedEventHandler(ProcessNextBatch);
                _pollTimer.AutoReset = false;
                _pollTimer.Start();
            }
            catch (Exception ex)
            {
                Log.Error("StartOperation :: Exception starting poll timer :: " + ex.Message);
            }
        }

        public void ProcessNextBatch(object sender, EventArgs args)
        {
            try
            {
                try { _pollTimer.Stop(); }
                catch (Exception ex) { Log.Error("Exception stopping timer :: " + ex.Message); }

                WatcherConfig config = null;
                try
                {
                    config = ConfigRepository.GetWatcherConfigByName("INCOMING_ORDERS");
                }
                catch (Exception ex)
                {
                    Log.Error("Exception fetching watcher config :: " + ex.Message);
                }

                try
                {
                    _pingStatus = CheckWatcherPing();
                }
                catch (Exception ex)
                {
                    Log.Error("Exception checking watcher ping :: " + ex.Message);
                }

                if (_pingStatus == true)
                {
                    if (config != null)
                    {
                        try
                        {
                            _connection = ConnectToWatcher(config.WatcherUrl);
                        }
                        catch (Exception ex)
                        {
                            Log.Error("Exception connecting to watcher :: " + ex.Message);
                        }

                        if (_connection != null && _connection.State == "CONNECTED")
                        {
                            string newFileFlag = ReadFlag("NEW_FILE_AVAILABLE");

                            if (newFileFlag == "True")
                            {
                                string rawLine = ReadFlag("ORDER_LINE").Trim();

                                // Checking format by raw line length, same as the
                                // legacy scanner's "new barcode vs old barcode" split.
                                if (rawLine.Length > 25 && rawLine != "ERROR")
                                {
                                    // ---- New / extended format ----
                                    string[] fields = rawLine.Split('|');
                                    string orderId = fields[0];
                                    string customerId = fields[1];
                                    string qty = fields[2];
                                    string orderDate = fields[3];
                                    string reference = fields[4];
                                    string batchNumber = fields[5];

                                    string importBatchId = orderId + "_" + DateTime.Now.ToString("yyyyMMdd_HHmmss");

                                    OrderRecord existing = null;
                                    try
                                    {
                                        existing = OrderRepository.GetByOrderId(orderId);
                                    }
                                    catch (Exception ex)
                                    {
                                        Log.Error("Exception fetching existing order :: " + ex.Message);
                                    }

                                    if (existing != null)
                                    {
                                        string processedFlag = ReadFlag("ORDER_PROCESSED");
                                        if (processedFlag == "False")
                                        {
                                            if (existing.ImportGenerated == 0)
                                            {
                                                CustomerProfile customer = null;
                                                try
                                                {
                                                    customer = CustomerRepository.GetByCustomerId(customerId);
                                                }
                                                catch (Exception ex)
                                                {
                                                    Log.Error("Exception fetching customer profile :: " + ex.Message);
                                                }

                                                if (customer != null)
                                                {
                                                    try
                                                    {
                                                        OrderRepository.UpdateFull(importBatchId, customer.Name, customer.Tier,
                                                            int.Parse(qty), batchNumber, "COMPLETE", existing.OrderRecordId);
                                                    }
                                                    catch (Exception ex)
                                                    {
                                                        Log.Error("Exception updating order record :: " + ex.Message);
                                                    }

                                                    try { WriteFlag("ORDER_PROCESSED", "True"); }
                                                    catch (Exception ex) { Log.Error("Exception writing processed flag :: " + ex.Message); }
                                                }
                                            }
                                        }
                                    }
                                    else
                                    {
                                        try
                                        {
                                            OrderRepository.Insert(orderId, importBatchId, customerId, "UNKNOWN",
                                                int.Parse(qty), batchNumber, "PENDING");
                                        }
                                        catch (Exception ex)
                                        {
                                            Log.Error("Exception inserting new order :: " + ex.Message);
                                        }
                                    }
                                }
                                else if (rawLine.Length < 25)
                                {
                                    // ---- Old / legacy format ----
                                    string importBatchId = rawLine + "_" + DateTime.Now.ToString("yyyyMMdd_HHmmss");

                                    OrderRecord existing = null;
                                    try
                                    {
                                        existing = OrderRepository.GetByOrderId(rawLine);
                                    }
                                    catch (Exception ex)
                                    {
                                        Log.Error("Exception fetching existing order :: " + ex.Message);
                                    }

                                    if (existing != null)
                                    {
                                        string processedFlag = ReadFlag("ORDER_PROCESSED");
                                        if (processedFlag == "False")
                                        {
                                            if (existing.ImportGenerated == 0)
                                            {
                                                try
                                                {
                                                    OrderRepository.UpdateImportFlagsOnly(importBatchId, existing.OrderRecordId);
                                                    WriteFlag("ORDER_PROCESSED", "True");
                                                }
                                                catch (Exception ex)
                                                {
                                                    Log.Error("Exception updating order record :: " + ex.Message);
                                                }
                                            }
                                        }
                                    }
                                    else
                                    {
                                        try
                                        {
                                            // Legacy format carries no customer/qty data — placeholder defaults.
                                            OrderRepository.Insert(rawLine, importBatchId, "UNKNOWN", "legacy-import",
                                                1, "GEN", "COMPLETE");
                                        }
                                        catch (Exception ex)
                                        {
                                            Log.Error("Exception inserting legacy order :: " + ex.Message);
                                        }
                                    }
                                }
                            }
                            else
                            {
                                // No new file — reset the processed flag if it's stuck set.
                                string processedFlag = ReadFlag("ORDER_PROCESSED");
                                if (processedFlag == "True")
                                {
                                    try { WriteFlag("ORDER_PROCESSED", "False"); }
                                    catch (Exception ex) { Log.Error("Exception resetting processed flag :: " + ex.Message); }
                                }
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error("ProcessNextBatch :: Unhandled exception :: " + ex.Message);
            }
            finally
            {
                try { _pollTimer.Start(); }
                catch (Exception ex) { Log.Error("Exception restarting timer :: " + ex.Message); }
            }
        }

        private bool CheckWatcherPing() { /* ... */ return true; }
        private WatcherConnection ConnectToWatcher(string url) { /* ... */ return null; }
        private string ReadFlag(string name) { /* ... */ return ""; }
        private void WriteFlag(string name, string value) { /* ... */ }
    }
}
