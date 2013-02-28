#include<stdio.h>
#include<mongo.h>
#include<stdbool.h>
#include<unistd.h>
#include<gridfs.h>
#include<signal.h>
#include<chromaprint.h>
#include<libavformat/avformat.h>
#include<libavutil/log.h>

#define MIN(a,b) ((a) < (b) ? (a) : (b))
#define CHROMAPRINT_BUFFER_SIZE (AVCODEC_MAX_AUDIO_FRAME_SIZE * 2)
#define MAX_IO_BUFFER_SIZE 4096 * 8
#define ETHER_OK 0
#define ETHER_ERROR 1

static mongo conn[1];
static gridfs fs;


/* BSON command to pop an entry off the queue.*/
static bson pop_cmd[1];
static bson_oid_t *queue_entry_id;
static ChromaprintContext chromaprint_context;

static bool interupted; 

static unsigned char *io_buffer;

static AVInputFormat *input_format;

int init_ffmpeg(void){
    fprintf(stderr, "Initializing ffmpeg... ");
    av_register_all();
    av_log_set_level(AV_LOG_VERBOSE);

    io_buffer = (unsigned char *)av_malloc(MAX_IO_BUFFER_SIZE);

    if((input_format = av_find_input_format("mp3")) == NULL){
        fprintf(stderr, "find format failed.\n");
       return ETHER_ERROR; 
    }
    fprintf(stderr, "success.\n");
    return ETHER_OK;
}

int init_mongodb(void){
    fprintf(stderr, "Initializing:\n");

    fprintf(stderr, "Connecting to mongodb... ");
    if (mongo_connect(conn, "127.0.0.1", 27017) != MONGO_OK){
        fprintf(stderr, " failed\n");
        return ETHER_ERROR;
    }
    fprintf(stderr, "success\n");
    return ETHER_OK;
}

void init_chromaprint(void){
    fprintf(stderr, "Initializing chromaprint.\n");
    chromaprint_context = chromaprint_new(CHROMAPRINT_ALGORITHM_DEFAULT);
}

int init_gridfs(void){
    fprintf(stderr, "Initializing gridfs... ");
    if(gridfs_init(conn, "test", "fs", &fs) != MONGO_OK){
        fprintf(stderr, "failed.\n");
        return ETHER_ERROR;
    }
    fprintf(stderr, "success.\n");
    return ETHER_OK;
}


void init_pop_cmd(void){
    bson_init(pop_cmd);

    bson_append_string(pop_cmd, "findAndModify", "queue");

    bson_append_start_object(pop_cmd, "query");
        bson_append_string(pop_cmd, "stage", "fingerprint");
    bson_append_finish_object(pop_cmd);

    bson_append_start_object(pop_cmd, "update");
        bson_append_start_object(pop_cmd, "$set");
            bson_append_string(pop_cmd, "stage", "fingerprint_inprogress");
        bson_append_finish_object(pop_cmd);
    bson_append_finish_object(pop_cmd);

    bson_append_start_object(pop_cmd, "sort");
        bson_append_int(pop_cmd, "priority", -1);
    bson_append_finish_object(pop_cmd);

    bson_finish(pop_cmd);
}

int read_func(void *opaque, uint8_t *buf, int buf_size){
    return (int) gridfile_read((gridfile *) opaque, (gridfs_offset) buf_size, (char *) buf);
}

int64_t seek_func(void *opaque, int64_t offset, int whence){
    if (whence == AVSEEK_SIZE){
        return (int64_t) gridfile_get_contentlength((gridfile *) opaque);
    } else {
        return (int64_t) gridfile_seek((gridfile *) opaque, (gridfs_offset) offset);
    }
}

//TODO: remaining and frame_count
static int remaining;
int decode_frame(AVCodecContext *decoder_context, AVPacket *packet, int *frame_count){
    AVFrame *frame = avcodec_alloc_frame();
    int got_frame = 0;

    avcodec_decode_audio4(decoder_context, frame, &got_frame, packet);

    if (got_frame){
        *frame_count = *frame_count + 1;
        if (*frame_count == 1){
            chromaprint_start(chromaprint_context,
                    decoder_context->sample_rate,
                    decoder_context->channels);
            remaining = 120 * decoder_context->channels * decoder_context->sample_rate;
        }
        int data_size = av_samples_get_buffer_size(NULL,
                decoder_context->channels,
                frame->nb_samples,
                decoder_context->sample_fmt,
                1);

        int to_feed = MIN(remaining, data_size / 2);
        remaining -= to_feed;
        if(remaining > 0){
            chromaprint_feed(chromaprint_context, frame->data[0], to_feed);
        } else {
            avcodec_free_frame(&frame);
            return -1;
        }
    }

    avcodec_free_frame(&frame);

    return 0;
}

int get_fingerprint(gridfile *gfile, const char *filename, char **fingerprint_buffer, int *duration){
    AVIOContext *io_context = avio_alloc_context(
            io_buffer,
            MAX_IO_BUFFER_SIZE,
            0,
            gfile,
            read_func,
            NULL,
            seek_func);

    AVFormatContext *format_context = avformat_alloc_context();

    format_context->pb = io_context;

    avformat_open_input(&format_context, filename, input_format, NULL);

    int stream_index = av_find_best_stream(format_context, AVMEDIA_TYPE_AUDIO, -1, -1, NULL, 0);

    AVStream *stream = format_context->streams[stream_index];

    *duration = (stream->duration / stream->time_base.den);

    AVCodecContext *decoder_context = stream->codec;

    AVCodec *decoder = avcodec_find_decoder(decoder_context->codec_id);

    avcodec_open2(decoder_context, decoder, NULL);

    AVPacket packet;
    int frame_count = 0;
    while(av_read_frame(format_context, &packet)>=0){
        if (decode_frame(decoder_context, &packet, &frame_count) == -1){
            av_free_packet(&packet);
            break;
        }
        av_free_packet(&packet);
    }

    chromaprint_finish(chromaprint_context);

    chromaprint_get_fingerprint(chromaprint_context, fingerprint_buffer);

    avcodec_close(decoder_context);

    avformat_close_input(&format_context);

    //avformat_free_context(format_context);

    av_free(io_context);
}

/* Release the file back to the next stage of the queue.
   */
void set_queue_stage(void){
    bson cmd[1];
    bson queue_query[1];

    bson_init(queue_query);
    bson_append_oid(queue_query, "_id", queue_entry_id);
    bson_finish(queue_query);

    bson_init(cmd);
    bson_append_start_object(cmd, "$set");
        bson_append_string(cmd, "stage", "metadata");
    bson_append_finish_object(cmd);

    bson_finish(cmd);

    mongo_update(conn, "test.queue", queue_query, cmd, MONGO_UPDATE_BASIC, NULL);

    bson_destroy(cmd);
    bson_destroy(queue_query);
}

int set_fingerprint(bson *gridfs_query, const char *fingerprint_buffer, int duration){
    bson cmd[1];
    bson_init(cmd);

    bson_append_start_object(cmd, "$set");
        bson_append_string(cmd, "fingerprint", fingerprint_buffer);
        bson_append_int(cmd, "duration", duration);
    bson_append_finish_object(cmd);

    bson_finish(cmd);

    mongo_update(conn, "test.fs.files", gridfs_query, cmd, MONGO_UPDATE_BASIC, NULL);

    set_queue_stage();

    bson_destroy(cmd);

    return 0;
}

int process_file(bson_oid_t *file_id){
    bson gridfs_query;
    bson_init(&gridfs_query);
    bson_append_oid(&gridfs_query, "_id", file_id);
    bson_finish(&gridfs_query);
    
    gridfile gfile;
    gridfs_find_query(&fs, &gridfs_query, &gfile);

    const char *filename = gridfile_get_filename(&gfile);
    printf("fingerprinting: %s\n", filename);

    char *fingerprint_buffer;

    int duration = 0;

    get_fingerprint(&gfile, filename, &fingerprint_buffer, &duration);

    set_fingerprint(&gridfs_query, fingerprint_buffer, duration);

    chromaprint_dealloc(fingerprint_buffer);

    gridfile_destroy(&gfile);

    bson_destroy(&gridfs_query);
}

int poll(){
    bson queue_entry[1];
    mongo_run_command(conn, "test", pop_cmd, queue_entry);
    bson_iterator iterator;
    bson_find(&iterator, queue_entry, "value");

    if (bson_iterator_more(&iterator) != 10){
        /* Popped an item off the queue. */
        printf("popped item...\n");

        bson value;
        bson_iterator_subobject(&iterator, &value);

        //bson_print(&value);

        bson_find(&iterator, &value, "file_id");

        bson_oid_t *file_id = bson_iterator_oid(&iterator);

        bson_find(&iterator, &value, "_id");

        queue_entry_id = bson_iterator_oid(&iterator);

        process_file(file_id);

        bson_destroy(queue_entry);
        return 0;
    }
    else {
        bson_destroy(queue_entry);
        return 1;
    }
}

void interuptHandler(int dummy){
    interupted = true;
}

void destroy_mongodb(void){
    mongo_destroy(conn);
}

void destroy_gridfs(void){
    gridfs_destroy(&fs);
}

void destroy_pop_cmd(){
    bson_destroy(pop_cmd);
}

void destroy_chromaprint(){
    chromaprint_free(chromaprint_context);
}

void destroy_ffmpeg(){
    av_free(io_buffer);
}

int main(void){
    if (init_ffmpeg() != ETHER_OK){
        goto init_ffmpeg_failed;
    }
    if (init_mongodb() != ETHER_OK){
        goto init_mongodb_failed;
    }
    if (init_gridfs() != ETHER_OK){
        goto init_gridfs_failed;
    }
//TODO: is error checking important here?
    init_pop_cmd();
    init_chromaprint();

    interupted = false;
    /* Start catching signals. */
    signal(SIGINT, interuptHandler);

    while(!interupted){
        /* Poll the queue and process any entries.
        If the queue is done, sleep for one second.
        */
        if(poll()!=0){
            printf("sleeping\n");
            sleep(1);
        }
    }

    destroy_chromaprint();
    destroy_pop_cmd();
init_gridfs_failed:
    destroy_gridfs();
init_mongodb_failed:
    destroy_mongodb();
init_ffmpeg_failed:
    destroy_ffmpeg();


    return 0;
}
