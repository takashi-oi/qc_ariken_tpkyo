                  logger.error(
                     "データベース接続エラー (試行 %d/%d): %s" % (
                         attempt + 1,
                         self.config.max_attempts,
                         e
                     )
                  ) 